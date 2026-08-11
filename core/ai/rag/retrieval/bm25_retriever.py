"""
BM25 sparse retriever for the MedAI hybrid RAG system.

The retriever maintains a persistent local BM25 index so that the
sparse index survives application restarts.

Architecture:

    DocumentChunk
         ↓
    BM25Retriever
         ↓
    Persistent BM25 index
         ↓
    Ranked search results
"""

from __future__ import annotations

import pickle
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

from core.ai.rag.ingestion.document import DocumentChunk
from core.config.logging import get_logger


logger = get_logger(__name__)


@dataclass(slots=True)
class BM25Result:
    """Result returned by the BM25 retriever."""

    chunk_id: str
    score: float
    text: str
    document_id: str
    chunk_index: int
    metadata: dict[str, Any]


class BM25Retriever:
    """
    Persistent BM25 sparse retriever.

    The index is rebuilt from DocumentChunk objects and persisted
    locally so it can be restored after application restart.
    """

    def __init__(
        self,
        index_path: str | Path,
    ) -> None:
        self.index_path = Path(index_path)

        self._chunks: list[DocumentChunk] = []
        self._bm25: BM25Okapi | None = None

        self._load()

    # ------------------------------------------------------------------
    # Tokenization
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """
        Tokenize text for BM25.

        Keeps alphanumeric terms and normalizes them to lowercase.
        """

        return re.findall(
            r"[a-zA-Z0-9]+",
            text.lower(),
        )

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def build(self, chunks: list[DocumentChunk]) -> None:
        """
        Build a BM25 index from document chunks.

        This replaces the existing index.
        """

        if not chunks:
            logger.warning(
                "Cannot build BM25 index: no chunks provided"
            )
            self._chunks = []
            self._bm25 = None
            return

        self._chunks = chunks

        tokenized_corpus = [
            self._tokenize(chunk.text)
            for chunk in chunks
        ]

        self._bm25 = BM25Okapi(tokenized_corpus)

        self._save()

        logger.info(
            "BM25 index built",
            chunks=len(chunks),
            index=str(self.index_path),
        )

    def add(self, chunks: list[DocumentChunk]) -> None:
        """
        Add chunks to the existing BM25 index.

        For correctness, the index is rebuilt after adding because
        BM25 corpus statistics depend on the complete corpus.
        """

        if not chunks:
            return

        existing = {
            chunk.chunk_id: chunk
            for chunk in self._chunks
        }

        for chunk in chunks:
            existing[chunk.chunk_id] = chunk

        self.build(list(existing.values()))

    def remove(self, chunk_ids: set[str]) -> None:
        """
        Remove chunks from the index and rebuild it.
        """

        if not chunk_ids:
            return

        remaining = [
            chunk
            for chunk in self._chunks
            if chunk.chunk_id not in chunk_ids
        ]

        self.build(remaining)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
    ) -> list[BM25Result]:
        """
        Search the BM25 index.

        Args:
            query: User search query.
            top_k: Maximum number of results.

        Returns:
            Ranked BM25 results.
        """

        if not query.strip():
            return []

        if self._bm25 is None or not self._chunks:
            logger.warning("BM25 index is empty")
            return []

        query_tokens = self._tokenize(query)

        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda index: scores[index],
            reverse=True,
        )[:top_k]

        results = []

        for index in ranked_indices:
            chunk = self._chunks[index]

            results.append(
                BM25Result(
                    chunk_id=chunk.chunk_id,
                    score=float(scores[index]),
                    text=chunk.text,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    metadata=chunk.metadata,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        """Persist the chunk corpus required to rebuild the BM25 index."""

        self.index_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = {
            "chunks": self._chunks,
        }

        temporary_path = self.index_path.with_suffix(
            self.index_path.suffix + ".tmp"
        )

        with temporary_path.open("wb") as file:
            pickle.dump(
                data,
                file,
                protocol=pickle.HIGHEST_PROTOCOL,
            )

        temporary_path.replace(self.index_path)

    def _load(self) -> None:
        """Load the persisted corpus and rebuild the BM25 index."""

        if not self.index_path.exists():
            logger.info(
                "BM25 index not found; starting empty",
                index=str(self.index_path),
            )
            return

        try:
            with self.index_path.open("rb") as file:
                data = pickle.load(file)

            chunks = data.get("chunks", [])

            if not chunks:
                return

            self._chunks = chunks

            tokenized_corpus = [
                self._tokenize(chunk.text)
                for chunk in chunks
            ]

            self._bm25 = BM25Okapi(tokenized_corpus)

            logger.info(
                "BM25 index loaded",
                chunks=len(chunks),
                index=str(self.index_path),
            )

        except Exception as exc:
            logger.error(
                "Failed to load BM25 index",
                index=str(self.index_path),
                error=str(exc),
            )

            self._chunks = []
            self._bm25 = None
            