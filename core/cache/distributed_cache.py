"""
Distributed Cache Service.
Provides high-performance, fault-tolerant Redis-backed distributed caching
with automatic JSON serialization, TTL expiration, pattern invalidation,
and graceful fallback on Redis degradation.
"""

import json
import time
from typing import Any, Callable, Optional, TypeVar
from pydantic import BaseModel

from core.config.logging import get_logger
from core.database.redis_client import get_redis
from core.database.redis_keys import NS_CACHE, DEFAULT_CACHE_TTL, key_cache

logger = get_logger("core.cache.distributed_cache")

T = TypeVar("T")


class DistributedCache:
    """
    Distributed Redis cache with resilient error handling.
    All operations gracefully handle Redis downtime by falling back or returning cache-miss.
    """

    def __init__(self, default_ttl: int = DEFAULT_CACHE_TTL) -> None:
        self.default_ttl = default_ttl
        # Local fallback cache: key -> (value_json, expiry_timestamp)
        self._local_fallback: dict[str, tuple[str, float]] = {}

    def _clean_expired_local(self) -> None:
        now = time.time()
        expired = [k for k, (_, exp) in self._local_fallback.items() if exp <= now]
        for k in expired:
            self._local_fallback.pop(k, None)

    async def get(self, key: str, domain: str = "general") -> Any | None:
        """
        Get value from cache.
        Returns deserialized JSON data or None if not found/expired/error.
        """
        full_key = key_cache(domain, key)
        try:
            redis = get_redis()
            raw = await redis.get(full_key)
            if raw is not None:
                try:
                    return json.loads(raw)
                except Exception:
                    return raw
        except Exception as e:
            logger.debug(f"Redis get failed for key '{full_key}', checking local fallback: {e}")
            self._clean_expired_local()
            if full_key in self._local_fallback:
                val_str, exp = self._local_fallback[full_key]
                if exp > time.time():
                    try:
                        return json.loads(val_str)
                    except Exception:
                        return val_str
                else:
                    self._local_fallback.pop(full_key, None)
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
        domain: str = "general",
    ) -> bool:
        """
        Store value in cache with TTL.
        Handles dicts, lists, primitives, and Pydantic models.
        """
        full_key = key_cache(domain, key)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl

        try:
            if isinstance(value, BaseModel):
                serialized = value.model_dump_json()
            elif isinstance(value, (dict, list, bool, int, float)) or value is None:
                serialized = json.dumps(value)
            elif isinstance(value, str):
                # Check if it's already a valid json string or plain string
                serialized = json.dumps(value)
            else:
                serialized = json.dumps(str(value))
        except Exception as ser_err:
            logger.warning(f"Failed to serialize cache value for '{full_key}': {ser_err}")
            return False

        # Store in local fallback
        self._local_fallback[full_key] = (serialized, time.time() + ttl)

        try:
            redis = get_redis()
            await redis.setex(full_key, ttl, serialized)
            return True
        except Exception as e:
            logger.debug(f"Redis set failed for key '{full_key}', retained in local fallback: {e}")
            return False

    async def delete(self, key: str, domain: str = "general") -> bool:
        """Delete a key from cache."""
        full_key = key_cache(domain, key)
        self._local_fallback.pop(full_key, None)
        try:
            redis = get_redis()
            res = await redis.delete(full_key)
            return res > 0
        except Exception as e:
            logger.debug(f"Redis delete failed for key '{full_key}': {e}")
            return False

    async def exists(self, key: str, domain: str = "general") -> bool:
        """Check if key exists in cache."""
        full_key = key_cache(domain, key)
        try:
            redis = get_redis()
            return bool(await redis.exists(full_key))
        except Exception as e:
            logger.debug(f"Redis exists check failed for '{full_key}': {e}")
            self._clean_expired_local()
            return full_key in self._local_fallback

    async def invalidate_pattern(self, pattern: str, domain: str = "general") -> int:
        """
        Invalidate all keys matching a pattern within a domain.
        Example: invalidate_pattern("doctor:*", domain="doctors")
        """
        search_pattern = key_cache(domain, pattern)
        deleted_count = 0

        # Invalidate local fallback matching pattern
        prefix = key_cache(domain, "")
        local_keys = [k for k in self._local_fallback if k.startswith(prefix)]
        for k in local_keys:
            self._local_fallback.pop(k, None)

        try:
            redis = get_redis()
            async for k in redis.scan_iter(match=search_pattern, count=100):
                await redis.delete(k)
                deleted_count += 1
        except Exception as e:
            logger.debug(f"Redis pattern invalidation failed for '{search_pattern}': {e}")

        return deleted_count

    async def clear_domain(self, domain: str) -> int:
        """Clear all cached keys for a specific domain namespace."""
        return await self.invalidate_pattern("*", domain=domain)


# Singleton distributed cache instance
cache = DistributedCache()
