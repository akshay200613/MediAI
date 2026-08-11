"""
Semantic reranker for MedAI hybrid retrieval.

Takes the candidates produced by dense + sparse retrieval and
reranks them according to their relevance to the user's query.

Pipeline:

    Qdrant + BM25
          ↓
        RRF
          ↓
      Reranker
          ↓
    Final context
"""

from __future__ import annotations

import json
from typing import Any

from core.ai.llm.client import (BaseLLMClient,Message,)
from core.ai.rag.retrieval.fusion import FusionResult
from core.config.logging import get_logger


logger = get_logger(__name__)


class Reranker:
    """
    Reranks hybrid retrieval candidates using the LLM.

    The reranker does not retrieve new documents.
    It only decides which already-retrieved candidates are most
    relevant to the user's query.
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        *,
        top_k: int = 5,
    ) -> None:
        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        self.llm = llm_client
        self.top_k = top_k

    async def rerank(
        self,
        query: str,
        candidates: list[FusionResult],
        *,
        top_k: int | None = None,
    ) -> list[FusionResult]:
        """
        Rerank hybrid retrieval candidates.

        Args:
            query:
                Original user question.

            candidates:
                Results produced by RRF.

            top_k:
                Number of results to return.

        Returns:
            Reranked FusionResult objects.
        """

        if not candidates:
            return []

        final_top_k = min(
            top_k or self.top_k,
            len(candidates),
        )

        # --------------------------------------------------------------
        # Prepare candidates for the LLM
        # --------------------------------------------------------------

        candidate_data: list[dict[str, Any]] = []

        for index, candidate in enumerate(
            candidates
        ):
            candidate_data.append(
                {
                    "candidate_id": index,
                    "text": candidate.text,
                    "metadata": candidate.metadata,
                }
            )

        prompt = self._build_prompt(
            query=query,
            candidates=candidate_data,
        )

        try:
            response = await self.llm.generate(
                messages=[
                    Message(
                        role="user",
                        content= prompt,
                    )
                ],
                system_prompt=(
                    "You are a retrieval reranking system. "
                    "Your task is to rank retrieved knowledge-base "
                    "chunks by their relevance to the user's question. "
                    "Do not answer the question. "
                    "Return only valid JSON."
                ),
                temperature=0.0,
                max_tokens=1000,
            )

            rankings = self._parse_response(
                response.content
            )

            if not rankings:
                logger.warning(
                    "Reranker returned no valid rankings"
                )

                return candidates[:final_top_k]

            reranked = self._apply_rankings(
                candidates=candidates,
                rankings=rankings,
                top_k=final_top_k,
            )

            logger.debug(
                "Reranking completed",
                query=query,
                candidates=len(candidates),
                results=len(reranked),
            )

            return reranked

        except Exception as exc:
            logger.error(
                "Reranking failed",
                query=query,
                error=str(exc),
            )

            # Retrieval should never completely fail because
            # the reranker is unavailable.
            return candidates[:final_top_k]

    @staticmethod
    def _build_prompt(
        *,
        query: str,
        candidates: list[dict[str, Any]],
    ) -> str:
        """Build the reranking prompt."""

        candidate_text = json.dumps(
            candidates,
            ensure_ascii=False,
            indent=2,
        )

        return f"""
Rank the following knowledge-base candidates according to how
relevant they are to the user's question.

USER QUESTION:
{query}

CANDIDATES:
{candidate_text}

Rules:

1. Rank only the provided candidates.
2. Do not invent information.
3. Prefer candidates that directly answer the question.
4. Prefer specific information over generic information.
5. Prefer the candidate containing the exact requested information.
6. Return the most relevant candidates first.
7. Return ONLY valid JSON.

Required format:

[
  {{
    "candidate_id": 0,
    "score": 0.95
  }},
  {{
    "candidate_id": 2,
    "score": 0.82
  }}
]

Use a relevance score between 0 and 1.
""".strip()

    @staticmethod
    def _parse_response(
        content: str,
    ) -> list[dict[str, Any]]:
        """
        Parse the LLM's JSON response.

        Handles occasional markdown code fences.
        """

        content = content.strip()

        if content.startswith("```"):
            lines = content.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            content = "\n".join(lines).strip()

        try:
            data = json.loads(content)

        except json.JSONDecodeError:
            logger.warning(
                "Invalid JSON returned by reranker"
            )
            return []

        if not isinstance(data, list):
            return []

        valid_rankings: list[dict[str, Any]] = []

        for item in data:
            if not isinstance(item, dict):
                continue

            candidate_id = item.get(
                "candidate_id"
            )

            score = item.get("score")

            if not isinstance(
                candidate_id,
                int,
            ):
                continue

            if not isinstance(
                score,
                (int, float),
            ):
                continue

            valid_rankings.append(
                {
                    "candidate_id": candidate_id,
                    "score": max(
                        0.0,
                        min(1.0, float(score)),
                    ),
                }
            )

        return valid_rankings

    @staticmethod
    def _apply_rankings(
        *,
        candidates: list[FusionResult],
        rankings: list[dict[str, Any]],
        top_k: int,
    ) -> list[FusionResult]:
        """Apply reranker scores to candidates."""

        ranked_candidates: list[
            tuple[float, int, FusionResult]
        ] = []

        seen: set[int] = set()

        for ranking in rankings:
            candidate_id = ranking[
                "candidate_id"
            ]

            if candidate_id in seen:
                continue

            if not (
                0 <= candidate_id < len(candidates)
            ):
                continue

            seen.add(candidate_id)

            ranked_candidates.append(
                (
                    ranking["score"],
                    candidate_id,
                    candidates[candidate_id],
                )
            )

        ranked_candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return [
            candidate
            for _, _, candidate in ranked_candidates[:top_k]
        ]
