"""
Hybrid retrieval for the MedAI RAG system.

Retrieval pipeline:

    Dense retrieval (Qdrant)
              +
    Sparse retrieval (BM25)
              ↓
        RRF Fusion
              ↓
         Reranking
              ↓
       Final candidates

The rest of the RAG pipeline interacts only with this class.
"""

from __future__ import annotations

from typing import Any

from core.ai.llm.client import BaseLLMClient
from core.ai.rag.retrieval.bm25_retriever import BM25Retriever
from core.ai.rag.retrieval.fusion import (
    FusionResult,
    reciprocal_rank_fusion,
)
from core.ai.rag.retrieval.qdrant_retriever import QdrantRetriever
from core.ai.rag.retrieval.reranker import Reranker
from core.config.logging import get_logger


logger = get_logger(__name__)


class HybridRetriever:
    """
    Production-oriented hybrid retriever.

    Combines:

        1. Dense semantic retrieval
        2. Sparse lexical retrieval
        3. Reciprocal Rank Fusion
        4. Semantic reranking
    """

    def __init__(
        self,
        qdrant_retriever: QdrantRetriever,
        bm25_retriever: BM25Retriever,
        llm_client: BaseLLMClient,
        *,
        dense_top_k: int = 10,
        sparse_top_k: int = 10,
        fusion_top_k: int = 10,
        rerank_top_k: int = 5,
        rrf_k: int = 60,
        enable_reranking: bool = True,
    ) -> None:
        if dense_top_k <= 0:
            raise ValueError(
                "dense_top_k must be greater than zero."
            )

        if sparse_top_k <= 0:
            raise ValueError(
                "sparse_top_k must be greater than zero."
            )

        if fusion_top_k <= 0:
            raise ValueError(
                "fusion_top_k must be greater than zero."
            )

        if rerank_top_k <= 0:
            raise ValueError(
                "rerank_top_k must be greater than zero."
            )

        if rrf_k <= 0:
            raise ValueError(
                "rrf_k must be greater than zero."
            )

        if rerank_top_k > fusion_top_k:
            raise ValueError(
                "rerank_top_k cannot be greater than "
                "fusion_top_k."
            )

        self.qdrant = qdrant_retriever
        self.bm25 = bm25_retriever

        self.dense_top_k = dense_top_k
        self.sparse_top_k = sparse_top_k
        self.fusion_top_k = fusion_top_k
        self.rerank_top_k = rerank_top_k
        self.rrf_k = rrf_k
        self.enable_reranking = enable_reranking

        self.reranker = Reranker(
            llm_client,
            top_k=rerank_top_k,
        )

    async def search(
        self,
        *,
        query: str,
        query_vector: list[float],
        filters: dict[str, Any] | None = None,
        score_threshold: float = 0.0,
    ) -> list[FusionResult]:
        """
        Perform hybrid retrieval followed by reranking.

        Pipeline:

            Query
              ↓
        ┌───────────────┐
        │ Dense + Sparse│
        └───────┬───────┘
                ↓
              RRF
                ↓
          RRF candidates
                ↓
            Reranker
                ↓
          Final results
        """

        # ==============================================================
        # 1. Dense retrieval
        # ==============================================================

        dense_results = await self.qdrant.search(
            query_vector=query_vector,
            top_k=self.dense_top_k,
            score_threshold=score_threshold,
            filters=filters,
        )

        # ==============================================================
        # 2. Sparse retrieval
        # ==============================================================

        sparse_results = self.bm25.search(
            query,
            top_k=self.sparse_top_k,
        )

        logger.debug(
            "Hybrid retrieval candidates",
            query=query,
            dense_results=len(dense_results),
            sparse_results=len(sparse_results),
        )

        # ==============================================================
        # 3. Reciprocal Rank Fusion
        # ==============================================================

        fused_results = reciprocal_rank_fusion(
            [
                dense_results,
                sparse_results,
            ],
            k=self.rrf_k,
            top_k=self.fusion_top_k,
            dense_weight=0.65,
            sparse_weight=0.35
        )

        logger.debug(
            "RRF fusion completed",
            query=query,
            fused_results=len(fused_results),
        )

        if not fused_results:
            logger.warning(
                "Hybrid retrieval returned no results",
                query=query,
            )

            return []

        # ==============================================================
        # 4. Optional reranking
        # ==============================================================

        if not self.enable_reranking:
            return fused_results[:self.rerank_top_k]

        reranked_results = await self.reranker.rerank(
            query=query,
            candidates=fused_results,
            top_k=self.rerank_top_k,
        )

        logger.debug(
            "Hybrid reranking completed",
            query=query,
            candidates=len(fused_results),
            final_results=len(reranked_results),
        )

        return reranked_results
