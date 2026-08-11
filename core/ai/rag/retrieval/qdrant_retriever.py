"""
Qdrant Retriever – vector similarity search with optional filters.
"""

from alembic.util import exc
from mako import filters
from typing import Any

from qdrant_client.models import Filter, FieldCondition, MatchValue

from core.database.qdrant_client import get_qdrant_client
from core.config.logging import get_logger

logger = get_logger(__name__)


class QdrantRetriever:
    """
    Retrieves relevant document chunks from a Qdrant collection.
    Supports dense vector search and metadata filtering.
    """

    def __init__(self, collection_name: str) -> None:
        self.collection_name = collection_name
        self.client = get_qdrant_client()

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        score_threshold: float = 0.7,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform vector similarity search.

        Returns:
            List of dicts with 'score' and 'payload' keys.
        """

        qdrant_filter = None

        if filters:
            conditions = [
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value),
                )
                for key, value in filters.items()
            ]

            qdrant_filter = Filter(must=conditions)

        try:
            result = await self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=top_k,
                score_threshold=score_threshold,
                query_filter=qdrant_filter,
                with_payload=True,
            )

            return [
                {
                    "score": point.score,
                    "payload": point.payload or {},
                    "id": str(point.id),
                }
                for point in result.points
            ]

        except Exception as exc:
            logger.error(
                "Qdrant search failed",
                error=str(exc),
                collection=self.collection_name,
            )
            return []

    async def upsert(self, points: list[dict[str, Any]]) -> None:
        """
        Upsert points (chunks + embeddings) into the collection.
        Auto-creates the collection if it doesn't exist.
        """
        from core.database.qdrant_client import ensure_collection
        from qdrant_client.models import PointStruct
        import uuid

        if not points:
            return

        vector_size = len(points[0]["vector"])
        await ensure_collection(self.collection_name, vector_size=vector_size)

        qdrant_points = [
            PointStruct(
                id=point.get("id") or str(uuid.uuid4()),
                vector=point["vector"],
                payload=point.get("payload", {}),
            )
            for point in points
        ]

        await self.client.upsert(
            collection_name=self.collection_name,
            points=qdrant_points,
        )
        logger.info("Points upserted", count=len(points), collection=self.collection_name)
