import asyncio

from core.ai.llm.gemini_client import get_llm_client


async def main():
    client = get_llm_client()

    document_embedding = await client.embed(
        "BMH Kozhikode provides cardiology services.",
        task_type="RETRIEVAL_DOCUMENT",
    )

    query_embedding = await client.embed(
        "Does BMH have cardiology?",
        task_type="RETRIEVAL_QUERY",
    )

    print("Document embedding dimension:", len(document_embedding))
    print("Query embedding dimension:", len(query_embedding))


if __name__ == "__main__":
    asyncio.run(main())