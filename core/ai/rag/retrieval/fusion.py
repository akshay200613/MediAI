"""
Reciprocal Rank Fusion for hybrid retrieval.

Combines ranked results from dense and sparse retrievers into a
single ranking.

RRF score:

    RRF(d) = Σ 1 / (k + rank(d))

The actual similarity scores from Qdrant and BM25 are deliberately
not compared directly because they are on different scales.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass(slots=True)
class FusionResult:
    """A result produced by rank fusion."""

    chunk_id: str
    score: float
    text: str
    document_id: str
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)

    # Original retrieval scores, useful for debugging/evaluation.
    dense_score: float | None = None
    sparse_score: float | None = None

    # Original ranks.
    dense_rank: int | None = None
    sparse_rank: int | None = None


def reciprocal_rank_fusion(
    result_lists: Iterable[Iterable[Any]],
    *,
    k: int = 60,
    top_k: int = 10,
    dense_weight: float = 0.65,
    sparse_weight: float = 0.35,
) -> list[FusionResult]:
    """
    Combine multiple ranked result lists using RRF.

    Args:
        result_lists:
            Ranked results from dense/sparse retrievers.

        k:
            RRF smoothing constant. The standard value is 60.

        top_k:
            Maximum number of fused results.
            
        dense_weight:
            Weight applied to dense retrieval results.

        sparse_weight:
            Weight applied to sparse BM25 results.

    Returns:
        Fused results sorted by descending RRF score.
    """

    if k <= 0:
        raise ValueError("RRF k must be greater than zero.")

    if top_k <= 0:
        return []
    if dense_weight < 0 or sparse_weight < 0:
        raise ValueError(
            "Fusion weights cannot be negative."
        )

    if dense_weight + sparse_weight <= 0:
        raise ValueError(
            "At least one fusion weight must be greater than zero."
        )

    fused: dict[str, FusionResult] = {}

    for source_index, results in enumerate(result_lists):
        for rank, result in enumerate(results, start=1):
            chunk_id = _get_chunk_id(result)

            if not chunk_id:
                continue

            weight = (
                dense_weight
                if source_index == 0
                else sparse_weight
            )
            rrf_contribution = weight / (k + rank)

            if chunk_id not in fused:
                fused[chunk_id] = FusionResult(
                    chunk_id=chunk_id,
                    score=0.0,
                    text=_get_text(result),
                    document_id=_get_document_id(result),
                    chunk_index=_get_chunk_index(result),
                    metadata=_get_metadata(result),
                )

            fused_result = fused[chunk_id]
            fused_result.score += rrf_contribution

            # First result list = dense.
            if source_index == 0:
                fused_result.dense_rank = rank
                fused_result.dense_score = _get_score(result)

            # Second result list = sparse.
            elif source_index == 1:
                fused_result.sparse_rank = rank
                fused_result.sparse_score = _get_score(result)

    return sorted(
        fused.values(),
        key=lambda result: result.score,
        reverse=True,
    )[:top_k]


def _get_chunk_id(result: Any) -> str | None:
    """Extract chunk ID from a retrieval result."""

    if hasattr(result, "chunk_id"):
        return str(result.chunk_id)

    if isinstance(result, dict):
        chunk_id = result.get("chunk_id")

        if chunk_id:
            return str(chunk_id)

        # Qdrant result format.
        result_id = result.get("id")

        if result_id:
            return str(result_id)

    return None


def _get_score(result: Any) -> float:
    """Extract the original retrieval score."""

    if hasattr(result, "score"):
        return float(result.score)

    if isinstance(result, dict):
        return float(result.get("score", 0.0))

    return 0.0


def _get_text(result: Any) -> str:
    """Extract result text as a string."""

    if hasattr(result, "text"):
        return str(result.text)

    if isinstance(result, dict):
        text = result.get("text")

        if text is not None:
            return str(text)

        payload = result.get("payload", {})

        if isinstance(payload, dict):
            return str(payload.get("text", ""))

    return ""

def _get_document_id(result: Any) -> str:
    """Extract document ID as a string."""

    if hasattr(result, "document_id"):
        return str(result.document_id)

    if isinstance(result, dict):
        document_id = result.get("document_id")

        if document_id:
            return str(document_id)

        payload = result.get("payload", {})

        if isinstance(payload, dict):
            value = payload.get(
                "document_id",
                payload.get("source_id", ""),
            )
            return str(value)

    return ""


def _get_chunk_index(result: Any) -> int:
    """Extract chunk index as an integer."""

    if hasattr(result, "chunk_index"):
        return int(result.chunk_index)

    if isinstance(result, dict):
        chunk_index = result.get("chunk_index")

        if chunk_index is not None:
            return int(chunk_index)

        payload = result.get("payload", {})

        if isinstance(payload, dict):
            return int(
                payload.get("chunk_index", 0)
            )

    return 0


def _get_metadata(result: Any) -> dict[str, Any]:
    """Extract metadata."""

    if hasattr(result, "metadata"):
        metadata = result.metadata

        if isinstance(metadata, dict):
            return dict(metadata)

    if isinstance(result, dict):
        metadata = result.get("metadata")

        if isinstance(metadata, dict):
            return dict(metadata)

        payload = result.get("payload")

        if isinstance(payload, dict):
            return {
                str(key): value
                for key, value in payload.items()
                if key != "text"
            }

    return {}
    