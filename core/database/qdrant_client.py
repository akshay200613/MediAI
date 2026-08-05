"""
Qdrant Vector DB Client.
"""

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

from core.config.settings import settings

_client: AsyncQdrantClient | None = None


def get_qdrant_client() -> AsyncQdrantClient:
    """Get a singleton async Qdrant client."""
    global _client
    if _client is None:
        if settings.qdrant_api_key:
            _client = AsyncQdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                api_key=settings.qdrant_api_key,
            )
        else:
            _client = AsyncQdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
            )
    return _client


async def ensure_collection(
    collection_name: str,
    vector_size: int = 768,
    distance: Distance = Distance.COSINE,
) -> None:
    """Create a Qdrant collection if it doesn't exist."""
    client = get_qdrant_client()
    existing = await client.get_collections()
    names = [c.name for c in existing.collections]

    if collection_name not in names:
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=distance),
        )


async def close_qdrant_client() -> None:
    global _client
    if _client:
        await _client.close()
        _client = None
