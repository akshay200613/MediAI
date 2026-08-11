import asyncio

from core.ai.llm.gemini_client import get_llm_client
from core.ai.rag.pipeline import RAGPipeline
from core.config.settings import settings


QUESTIONS = [
    "What are the contact numbers of BMH Kozhikode?",
    "What facilities are available at BMH Kozhikode?",
    "What insurance and TPA services are available at BMH Kozhikode?",
    "What specialties and departments are available at BMH Kozhikode?",
]


async def main() -> None:
    llm = get_llm_client()

    collection_name = (
        f"{settings.qdrant_collection_prefix}_knowledge"
    )

    rag = RAGPipeline(
        llm_client=llm,
        collection_name=collection_name,
    )

    for question in QUESTIONS:
        print("\n" + "=" * 80)
        print(f"QUESTION: {question}")
        print("=" * 80)

        query_embedding = await llm.embed(
            question,
            task_type="RETRIEVAL_QUERY",
        )

        results = await rag.hybrid_retriever.search(
            query=question,
            query_vector=query_embedding,
            score_threshold=settings.rag_score_threshold,
        )

        if not results:
            print("NO RESULTS")
            continue

        for rank, result in enumerate(results, start=1):
            print(f"\n--- Rank {rank} ---")
            print(f"RRF Score     : {result.score:.6f}")
            print(f"Chunk ID      : {result.chunk_id}")
            print(f"Document ID   : {result.document_id}")
            print(f"Dense Score   : {result.dense_score}")
            print(f"Sparse Score  : {result.sparse_score}")
            print(f"Dense Rank    : {result.dense_rank}")
            print(f"Sparse Rank   : {result.sparse_rank}")
            print(f"Metadata      : {result.metadata}")
            print(f"Text          : {result.text[:500]}")


if __name__ == "__main__":
    asyncio.run(main())
    