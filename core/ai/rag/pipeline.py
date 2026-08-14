"""
RAG Pipeline for MedAI.

Architecture:

    INGESTION
        Document
            ↓
        DocumentChunk[]
            ├──→ Gemini embeddings → Qdrant
            └──→ BM25 index

    RETRIEVAL
        User Query
            ├──→ Gemini embedding → Qdrant
            └──→ Query text       → BM25
                         ↓
                    RRF Fusion
                         ↓
                  Hybrid Results
                         ↓
                    RAG Prompt
                         ↓
                      Gemini
                         ↓
                      Answer
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from core.ai.llm.client import BaseLLMClient, Message
from core.ai.rag.generation.prompt_builder import build_rag_prompt
from core.ai.rag.ingestion.chunker import chunk_document
from core.ai.rag.ingestion.document import Document, DocumentChunk
from core.ai.rag.ingestion.embedder import embed_texts
from core.ai.rag.retrieval.bm25_retriever import BM25Retriever
from core.ai.rag.retrieval.hybrid_retriever import HybridRetriever
from core.ai.rag.retrieval.qdrant_retriever import QdrantRetriever
from core.config.logging import get_logger
from core.config.settings import settings


logger = get_logger(__name__)


# ============================================================================
# Paths
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

BM25_INDEX_PATH = (
    PROJECT_ROOT
    / "data"
    / "indexes"
    / "bm25"
    / "medai_knowledge.pkl"
)


# ============================================================================
# Result model
# ============================================================================


@dataclass(slots=True)
class RAGResult:
    """Result returned by the RAG pipeline."""

    answer: str
    sources: list[dict[str, Any]] = field(
        default_factory=list
    )
    retrieved_chunks: int = 0
    query: str = ""


# ============================================================================
# RAG Pipeline
# ============================================================================


class RAGPipeline:
    """
    Main RAG orchestration layer.

    Responsibilities:

        - Document chunking
        - Embedding generation
        - Qdrant indexing
        - BM25 indexing
        - Hybrid retrieval
        - Prompt construction
        - LLM generation
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        collection_name: str,
        system_prompt: str = (
            "You are a helpful assistant for MedAI. "
            "Answer questions using the provided knowledge base context. "
            "Do not invent or assume information that is not present "
            "in the retrieved context. "
            "If the available context is insufficient, clearly say "
            "that the information is not available in the knowledge base."
        ),
        bm25_index_path: str | Path = BM25_INDEX_PATH,
    ) -> None:
        """
        Initialize the RAG pipeline.

        Args:
            llm_client:
                Gemini/LLM client implementing BaseLLMClient.

            collection_name:
                Qdrant collection used for dense retrieval.

            system_prompt:
                System instructions used during answer generation.

            bm25_index_path:
                Persistent path for the BM25 index.
        """

        self.llm = llm_client

        # ------------------------------------------------------------------
        # Dense retriever
        # ------------------------------------------------------------------

        self.retriever = QdrantRetriever(
            collection_name=collection_name,
        )

        # ------------------------------------------------------------------
        # Sparse retriever
        # ------------------------------------------------------------------

        self.bm25_retriever = BM25Retriever(
            index_path=bm25_index_path,
        )

        # ------------------------------------------------------------------
        # Hybrid retriever
        # ------------------------------------------------------------------

        self.hybrid_retriever = HybridRetriever(
           qdrant_retriever=self.retriever,
           bm25_retriever=self.bm25_retriever,
           llm_client=self.llm,
           dense_top_k=10,
           sparse_top_k=10,
           fusion_top_k=10,
           rerank_top_k=5,
           rrf_k=60,
           enable_reranking=True,
        )

        self.system_prompt = system_prompt

        logger.info(
            "RAG pipeline initialized",
            collection=collection_name,
            bm25_index=str(bm25_index_path),
        )

    # ========================================================================
    # INGESTION
    # ========================================================================

    async def prepare_chunks(
        self,
        document: Document,
    ) -> list[DocumentChunk]:
        """
        Convert a Document into reusable DocumentChunk objects.

        The same chunks are used by:

            Qdrant
            BM25
            Future reranking
            Future retrieval evaluation
        """

        return chunk_document(
            document,
            chunk_size=settings.rag_chunk_size,
            overlap=settings.rag_chunk_overlap,
        )

    async def index_chunks(
        self,
        chunks: list[DocumentChunk],
        *,
        update_bm25: bool = True,
    ) -> int:
        """
        Index chunks in Qdrant and optionally BM25.

        Args:
            chunks:
                DocumentChunk objects to index.

            update_bm25:
                Whether the BM25 index should be updated.

        Returns:
            Number of chunks indexed.
        """

        if not chunks:
            return 0

        # ------------------------------------------------------------------
        # Build metadata-enriched embedding text
        # ------------------------------------------------------------------

        embedding_inputs = [
            self._build_embedding_text(chunk)
            for chunk in chunks
        ]

        # ------------------------------------------------------------------
        # Generate Gemini document embeddings
        # ------------------------------------------------------------------

        embeddings = await embed_texts(
            embedding_inputs
        )

        if len(embeddings) != len(chunks):
            raise RuntimeError(
                "Embedding count does not match chunk count. "
                f"chunks={len(chunks)}, "
                f"embeddings={len(embeddings)}"
            )

        # ------------------------------------------------------------------
        # Build Qdrant points
        # ------------------------------------------------------------------

        points = []

        for chunk, embedding in zip(
            chunks,
            embeddings,
        ):
            points.append(
                {
                    "id": chunk.chunk_id,
                    "vector": embedding,
                    "payload": chunk.to_payload(),
                }
            )

        # ------------------------------------------------------------------
        # Qdrant dense index
        # ------------------------------------------------------------------

        await self.retriever.upsert(
            points
        )

        logger.info(
            "Chunks indexed in Qdrant",
            count=len(chunks),
            collection=self.retriever.collection_name,
        )

        # ------------------------------------------------------------------
        # BM25 sparse index
        # ------------------------------------------------------------------

        if update_bm25:
            self.bm25_retriever.add(
                chunks
            )

            logger.info(
                "Chunks indexed in BM25",
                count=len(chunks),
            )

        return len(chunks)

    async def ingest_document(
        self,
        document: Document,
    ) -> tuple[int, list[DocumentChunk]]:
        """
        Ingest a single Document.

        Returns:
            Tuple containing:

                chunk_count
                generated DocumentChunk objects
        """

        if not document.content.strip():
            logger.warning(
                "Skipping empty document",
                metadata=document.metadata,
            )

            return 0, []

        # ------------------------------------------------------------------
        # Document → chunks
        # ------------------------------------------------------------------

        chunks = await self.prepare_chunks(
            document
        )

        if not chunks:
            logger.warning(
                "No chunks generated",
                metadata=document.metadata,
            )

            return 0, []

        # ------------------------------------------------------------------
        # Chunks → Qdrant + BM25
        # ------------------------------------------------------------------

        await self.index_chunks(
            chunks
        )

        source_id = self._get_source_id(
            document
        )

        logger.info(
            "Document ingested",
            source_id=source_id,
            chunks=len(chunks),
            collection=self.retriever.collection_name,
        )

        return len(chunks), chunks

    async def ingest_documents(
        self,
        documents: list[Document],
    ) -> tuple[int, list[DocumentChunk]]:
        """
        Ingest multiple Documents.

        Returns:
            Tuple containing:

                total_chunks
                all_generated_chunks
        """

        if not documents:
            logger.warning(
                "No documents supplied for ingestion"
            )

            return 0, []

        total_chunks = 0
        all_chunks: list[DocumentChunk] = []

        for document in documents:
            chunk_count, chunks = (
                await self.ingest_document(
                    document
                )
            )

            total_chunks += chunk_count
            all_chunks.extend(chunks)

        logger.info(
            "Documents ingested",
            documents=len(documents),
            chunks=total_chunks,
            collection=self.retriever.collection_name,
        )

        return total_chunks, all_chunks

    async def ingest(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        source_id: str | None = None,
    ) -> int:
        """
        Backward-compatible raw text ingestion.

        Existing code can continue to call:

            await rag.ingest(...)
        """

        document_metadata = {
            **(metadata or {}),
        }

        if source_id:
            document_metadata[
                "source_id"
            ] = source_id

        document = Document(
            content=text,
            metadata=document_metadata,
        )

        chunk_count, _ = (
            await self.ingest_document(
                document
            )
        )

        return chunk_count

    # ========================================================================
    # QUERY / HYBRID RETRIEVAL
    # ========================================================================

    async def query(
        self,
        user_query: str,
        *,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
        conversation_history: list[Message] | None = None,
    ) -> RAGResult:
        """
        Execute the complete hybrid RAG pipeline.

        Pipeline:

            User Query
                ↓
            Gemini Query Embedding
                ↓
            ┌─────────────────┐
            │ Hybrid Retrieval│
            └────────┬────────┘
                     │
              ┌──────┴──────┐
              ▼             ▼
           Qdrant          BM25
              │             │
              └──────┬──────┘
                     ▼
                    RRF
                     ↓
               Top results
                     ↓
                RAG Prompt
                     ↓
                  Gemini
                     ↓
                  Answer
        """

        if not user_query or not user_query.strip():
            return RAGResult(
                answer="Please provide a question.",
                query=user_query,
            )

        # ------------------------------------------------------------------
        # Retrieval configuration
        # ------------------------------------------------------------------

        k = top_k or settings.rag_top_k

        # ------------------------------------------------------------------
        # Step 1: Generate query embedding
        # ------------------------------------------------------------------

        query_embedding = await self.llm.embed(
            user_query,
            task_type="RETRIEVAL_QUERY",
        )

        # ------------------------------------------------------------------
        # Step 2: Hybrid retrieval
        # ------------------------------------------------------------------

        retrieved = await self.hybrid_retriever.search(
            query=user_query,
            query_vector=query_embedding,
            filters=filters,
            score_threshold=settings.rag_score_threshold,
        )

        # Limit final results.
        retrieved = retrieved[:k]

        # ------------------------------------------------------------------
        # Step 3: No relevant information
        # ------------------------------------------------------------------

        if not retrieved:
            logger.warning(
                "No relevant chunks found",
                query=user_query,
            )

            return RAGResult(
                answer=(
                    "I don't have enough information in my "
                    "knowledge base to answer this question accurately."
                ),
                query=user_query,
            )

        # ------------------------------------------------------------------
        # Step 4: Build context
        # ------------------------------------------------------------------

        context_chunks = [
            result.text
            for result in retrieved
            if result.text.strip()
        ]

        if not context_chunks:
            logger.warning(
                "Retrieved results contain no usable text",
                query=user_query,
            )

            return RAGResult(
                answer=(
                    "I don't have enough information in my "
                    "knowledge base to answer this question accurately."
                ),
                query=user_query,
            )

        # ------------------------------------------------------------------
        # Step 5: Build source information
        # ------------------------------------------------------------------

        sources = [
            {
                "text": result.text[:200],
                "score": result.score,
                "chunk_id": result.chunk_id,
                "document_id": result.document_id,
                "chunk_index": result.chunk_index,
                "dense_score": result.dense_score,
                "sparse_score": result.sparse_score,
                "dense_rank": result.dense_rank,
                "sparse_rank": result.sparse_rank,
                **result.metadata,
            }
            for result in retrieved
        ]

        # ------------------------------------------------------------------
        # Step 6: Build RAG prompt
        # ------------------------------------------------------------------

        # Build source metadata list for enriched prompt context
        source_metadata = [
            {
                "category": result.metadata.get("category"),
                "title": result.metadata.get("title"),
                "hospital_name": result.metadata.get("hospital_name") or result.metadata.get("hospital"),
            }
            for result in retrieved
        ]

        messages = build_rag_prompt(
            query=user_query,
            context_chunks=context_chunks,
            conversation_history=(
                conversation_history or []
            ),
            source_metadata=source_metadata,
        )

        # ------------------------------------------------------------------
        # Step 7: Generate grounded answer
        # ------------------------------------------------------------------

        response = await self.llm.generate(
            messages,
            system_prompt=self.system_prompt,
        )

        logger.info(
            "RAG query completed",
            query=user_query,
            retrieved_chunks=len(retrieved),
        )

        return RAGResult(
            answer=response.content,
            sources=sources,
            retrieved_chunks=len(retrieved),
            query=user_query,
        )

    # ========================================================================
    # HELPERS
    # ========================================================================

    @staticmethod
    def _build_embedding_text(
        chunk: DocumentChunk,
    ) -> str:
        """
        Build metadata-enriched text for Gemini document embeddings.

        Including metadata improves retrieval for structured knowledge
        such as:

            - hospital facilities
            - doctors
            - insurance
            - policies
            - departments
            - medicines
        """

        metadata = chunk.metadata

        metadata_fields = {
            "hospital_name": "Hospital",
            "hospital": "Hospital",
            "category": "Category",
            "document_id": "Document",
            "source_id": "Source",
            "source_type": "Source type",
            "knowledge_base_path": "Knowledge domain",
        }

        metadata_lines: list[str] = []

        for key, label in metadata_fields.items():
            value = metadata.get(key)

            if value is None:
                continue

            if isinstance(value, str):
                value = value.strip()

            if value:
                metadata_lines.append(
                    f"{label}: {value}"
                )

        if not metadata_lines:
            return chunk.text

        return (
            "\n".join(metadata_lines)
            + "\n\n"
            + chunk.text
        )

    @staticmethod
    def _get_source_id(
        document: Document,
    ) -> str:
        """
        Resolve a stable source identifier.
        """

        source_id = (
            document.metadata.get(
                "document_id"
            )
            or document.metadata.get(
                "source_id"
            )
            or document.metadata.get(
                "source_file"
            )
        )

        if source_id:
            return str(source_id)

        return str(
            uuid5(
                NAMESPACE_URL,
                document.content[:500],
            )
        )
