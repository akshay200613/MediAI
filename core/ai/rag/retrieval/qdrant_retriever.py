"""
Qdrant Retriever – vector similarity search with optional filters.
"""

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
        score_threshold: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform vector similarity search.

        Note: ``score_threshold`` is applied in Python after fetching results
        rather than being passed to Qdrant directly, ensuring compatibility
        across all qdrant-client versions.

        Returns:
            List of dicts with 'score' and 'payload' keys, ordered by score desc.
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
            # Fetch more candidates than needed so Python-side threshold
            # filtering still returns up to top_k results.
            fetch_limit = max(top_k * 3, 20)

            result = await self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=fetch_limit,
                query_filter=qdrant_filter,
                with_payload=True,
            )

            # Filter by score threshold and cap at top_k
            filtered = [
                {
                    "score": point.score,
                    "payload": point.payload or {},
                    "id": str(point.id),
                }
                for point in result.points
                if point.score >= score_threshold
            ]

            return filtered[:top_k]

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
