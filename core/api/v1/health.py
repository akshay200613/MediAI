"""
Health Check Endpoints.
"""

from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from core.database.base import AsyncSessionLocal
from core.database.redis_client import get_redis
from core.config.settings import settings

router = APIRouter()


@router.get("", summary="System health check")
async def health() -> dict:
    """
    Returns the health status of all services:
    - API
    - PostgreSQL
    - Redis
    - Qdrant
    """
    checks: dict[str, str] = {}

    # PostgreSQL
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["postgres"] = "healthy"
    except Exception as e:
        checks["postgres"] = f"unhealthy: {e}"

    # Redis
    try:
        redis = get_redis()
        await redis.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {e}"

    # Qdrant
    try:
        from core.database.qdrant_client import get_qdrant_client
        client = get_qdrant_client()
        await client.get_collections()
        checks["qdrant"] = "healthy"
    except Exception as e:
        checks["qdrant"] = f"unhealthy: {e}"

    all_healthy = all("healthy" == v for v in checks.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.app_version,
        "environment": settings.environment,
        "services": checks,
    }
