"""
Health, Readiness, and Liveness Check Endpoints.
Provides comprehensive diagnostic probes for orchestrators (Kubernetes / Docker),
load balancers, and monitoring systems.
"""

from datetime import datetime, timezone
import time
from typing import Any

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from core.database.base import AsyncSessionLocal
from core.database.redis_client import get_redis
from core.config.settings import settings
from core.config.logging import get_logger

logger = get_logger("core.health")

router = APIRouter()


@router.get("/live", summary="Liveness probe", tags=["Health"])
@router.get("/healthz", summary="Liveness probe alias", tags=["Health"])
async def liveness_probe() -> dict[str, Any]:
    """
    Kubernetes / Container Liveness probe.
    Returns 200 OK fast to verify the process is alive.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.app_version,
    }


@router.get("/ready", summary="Readiness probe", tags=["Health"])
async def readiness_probe(response: Response) -> dict[str, Any]:
    """
    Kubernetes / Load Balancer Readiness probe.
    Verifies that critical dependencies (Database and Redis) are accepting queries.
    Returns 200 if ready, 503 if critical dependencies are down.
    """
    is_ready = True
    deps: dict[str, str] = {}

    # 1. Database check
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        deps["database"] = "ready"
    except Exception as e:
        is_ready = False
        deps["database"] = f"unready: {e}"
        logger.warning("Readiness probe DB check failed", error=str(e))

    # 2. Redis check
    try:
        redis = get_redis()
        await redis.ping()
        deps["redis"] = "ready"
    except Exception as e:
        # Redis is considered degraded but database is strictly required
        deps["redis"] = f"unready: {e}"
        logger.warning("Readiness probe Redis check failed", error=str(e))

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unready",
            "dependencies": deps,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "status": "ready",
        "dependencies": deps,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("", summary="Deep diagnostic health check", tags=["Health"])
@router.get("/", summary="Deep diagnostic health check", tags=["Health"])
async def deep_health_check(response: Response) -> dict[str, Any]:
    """
    Deep diagnostic health check.
    Measures latency and connectivity for:
    - PostgreSQL
    - Redis
    - Qdrant Vector Store
    - LLM Router Providers (Gemini & Groq)
    """
    checks: dict[str, dict[str, Any]] = {}
    is_critical_healthy = True

    # 1. PostgreSQL
    db_start = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_lat = round((time.perf_counter() - db_start) * 1000, 2)
        checks["postgres"] = {"status": "healthy", "latency_ms": db_lat}
    except Exception as e:
        is_critical_healthy = False
        checks["postgres"] = {"status": f"unhealthy: {e}", "latency_ms": None}

    # 2. Redis
    redis_start = time.perf_counter()
    try:
        redis = get_redis()
        await redis.ping()
        redis_lat = round((time.perf_counter() - redis_start) * 1000, 2)
        checks["redis"] = {"status": "healthy", "latency_ms": redis_lat}
    except Exception as e:
        checks["redis"] = {"status": f"degraded: {e}", "latency_ms": None}

    # 3. Qdrant
    qdrant_start = time.perf_counter()
    try:
        from core.database.qdrant_client import get_qdrant_client
        client = get_qdrant_client()
        await client.get_collections()
        qdrant_lat = round((time.perf_counter() - qdrant_start) * 1000, 2)
        checks["qdrant"] = {"status": "healthy", "latency_ms": qdrant_lat}
    except Exception as e:
        checks["qdrant"] = {"status": f"degraded: {e}", "latency_ms": None}

    # 4. LLM Providers
    llm_status: dict[str, Any] = {
        "gemini_configured": bool(settings.gemini_api_key),
        "groq_configured": bool(settings.groq_api_key),
        "cache_enabled": settings.litellm_cache_enabled,
    }
    if settings.gemini_api_key or settings.groq_api_key:
        llm_status["status"] = "healthy"
    else:
        llm_status["status"] = "degraded: no API keys configured"

    checks["llm"] = llm_status

    all_healthy = is_critical_healthy and all(
        c.get("status") == "healthy" for k, c in checks.items() if isinstance(c, dict) and "status" in c
    )

    if not is_critical_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        overall_status = "unhealthy"
    elif not all_healthy:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.app_version,
        "environment": settings.environment,
        "services": checks,
    }
