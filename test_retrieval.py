import asyncio

from core.ai.llm.gemini_client import get_llm_client
from core.ai.rag.retrieval.qdrant_retriever import QdrantRetriever


COLLECTION_NAME = "medai_knowledge"


async def test_query(question: str) -> None:
    """Test vector retrieval for a single question."""

    llm = get_llm_client()

    # 1. Convert user question into a query embedding
    query_embedding = await llm.embed(
        question,
        task_type="RETRIEVAL_QUERY",
    )

    print("\n" + "=" * 70)
    print(f"QUESTION: {question}")
    print("=" * 70)

    # 2. Search Qdrant
    retriever = QdrantRetriever(
        collection_name=COLLECTION_NAME
    )

    results = await retriever.search(
        query_vector=query_embedding,
        top_k=5,
        score_threshold=0.0,
    )

    # 3. Display results
    if not results:
        print("No results found.")
        return

    print(f"\nRetrieved {len(results)} chunks:\n")

    for index, result in enumerate(results, start=1):
        payload = result["payload"]

        print(f"--- Result {index} ---")
        print(f"Score: {result['score']}")
        print(f"Source ID: {payload.get('source_id')}")
        print(f"Category: {payload.get('category')}")
        print(f"Text:\n{payload.get('text')}")
        print()


async def main():
    questions = [
        "What are the contact numbers of BMH Kozhikode?",
        "What facilities are available at BMH Kozhikode?",
        "What insurance providers are associated with BMH?",
        "What specialties are available at BMH Kozhikode?",
    ]

    for question in questions:
        await test_query(question)


if __name__ == "__main__":
    asyncio.run(main())