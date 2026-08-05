"""
RAG Pipeline – orchestrates the full ingest → retrieve → generate cycle.
"""

from dataclasses import dataclass, field
from typing import Any

from core.ai.llm.client import BaseLLMClient, Message
from core.ai.rag.ingestion.chunker import chunk_text
from core.ai.rag.ingestion.embedder import embed_texts
from core.ai.rag.retrieval.qdrant_retriever import QdrantRetriever
from core.ai.rag.generation.prompt_builder import build_rag_prompt
from core.config.settings import settings
from core.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RAGResult:
    """Result from a RAG query."""
    answer: str
    sources: list[dict] = field(default_factory=list)
    retrieved_chunks: int = 0
    query: str = ""


class RAGPipeline:
    """
    Full RAG pipeline:
    1. Embed the query
    2. Retrieve relevant chunks from Qdrant
    3. Build a context-augmented prompt
    4. Generate an answer with the LLM
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        collection_name: str,
        system_prompt: str = "You are a helpful assistant. Use the provided context to answer questions accurately.",
    ) -> None:
        self.llm = llm_client
        self.retriever = QdrantRetriever(collection_name=collection_name)
        self.system_prompt = system_prompt

    async def ingest(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        source_id: str | None = None,
    ) -> int:
        """
        Ingest a document into the vector store.
        Returns the number of chunks indexed.
        """
        chunks = chunk_text(
            text,
            chunk_size=settings.rag_chunk_size,
            overlap=settings.rag_chunk_overlap,
        )
        embeddings = await embed_texts(chunks)

        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            points.append({
                "id": f"{source_id}_{i}" if source_id else None,
                "vector": embedding,
                "payload": {
                    "text": chunk,
                    "chunk_index": i,
                    "source_id": source_id,
                    **(metadata or {}),
                },
            })

        await self.retriever.upsert(points)
        logger.info("Document ingested", chunks=len(chunks), collection=self.retriever.collection_name)
        return len(chunks)

    async def query(
        self,
        user_query: str,
        *,
        top_k: int | None = None,
        filters: dict | None = None,
        conversation_history: list[Message] | None = None,
    ) -> RAGResult:
        """
        Query the RAG pipeline and return a grounded answer.
        """
        k = top_k or settings.rag_top_k

        # Step 1: Embed query
        from core.ai.llm.gemini_client import get_llm_client
        query_embedding = await get_llm_client().embed(user_query)

        # Step 2: Retrieve relevant chunks
        retrieved = await self.retriever.search(
            query_vector=query_embedding,
            top_k=k,
            score_threshold=settings.rag_score_threshold,
            filters=filters,
        )

        if not retrieved:
            logger.warning("No relevant chunks found", query=user_query)
            return RAGResult(
                answer="I don't have enough information to answer this question accurately.",
                query=user_query,
            )

        # Step 3: Build RAG prompt
        context_chunks = [r["payload"]["text"] for r in retrieved]
        sources = [
            {"text": r["payload"]["text"][:200], "score": r["score"], **{
                k: v for k, v in r["payload"].items() if k not in ("text",)
            }}
            for r in retrieved
        ]

        messages = build_rag_prompt(
            query=user_query,
            context_chunks=context_chunks,
            conversation_history=conversation_history or [],
        )

        # Step 4: Generate answer
        response = await self.llm.generate(
            messages,
            system_prompt=self.system_prompt,
        )

        return RAGResult(
            answer=response.content,
            sources=sources,
            retrieved_chunks=len(retrieved),
            query=user_query,
        )
