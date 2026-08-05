"""
Redis Client – async connection pool.
"""

from redis.asyncio import Redis, ConnectionPool
from core.config.settings import settings


_pool: ConnectionPool | None = None


def get_redis_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
    return _pool


def get_redis() -> Redis:
    """Get an async Redis client backed by the connection pool."""
    return Redis(connection_pool=get_redis_pool())


async def close_redis_pool() -> None:
    global _pool
    if _pool:
        await _pool.aclose()
        _pool = None
