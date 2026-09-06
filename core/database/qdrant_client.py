"""
Qdrant Vector Database Client.

Provides a singleton asynchronous Qdrant client and
collection management utilities.
"""

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

from core.config.settings import settings


_client: AsyncQdrantClient | None = None


def get_qdrant_client() -> AsyncQdrantClient:
    """
    Return the singleton asynchronous Qdrant client.
    """

    global _client

    if _client is None:
        if settings.qdrant_api_key:
            _client = AsyncQdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                api_key=settings.qdrant_api_key,
                https=True,
            )
        else:
            _client = AsyncQdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
            )

    return _client


async def ensure_collection(
    collection_name: str,
    vector_size: int | None = None,
    distance: Distance = Distance.COSINE,
) -> None:
    """
    Create a Qdrant collection if it does not already exist.

    The vector size defaults to the configured Gemini
    embedding dimension.
    """

    client = get_qdrant_client()

    if vector_size is None:
        vector_size = settings.gemini_embedding_dimension

    existing = await client.get_collections()

    collection_names = {
        collection.name
        for collection in existing.collections
    }

    if collection_name not in collection_names:
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=distance,
            ),
        )


async def close_qdrant_client() -> None:
    """Close the Qdrant client and reset the singleton."""

    global _client

    if _client is not None:
        await _client.close()
        _client = None