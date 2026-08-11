import asyncio

from core.database.qdrant_client import get_qdrant_client


async def main():
    client = get_qdrant_client()

    info = await client.get_collection(
        "medai_medai_knowledge"
    )

    print(info)


asyncio.run(main())
