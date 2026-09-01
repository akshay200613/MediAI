"""
Distributed Lock for Worker-Safe Execution.
Provides Redis-backed distributed locks with ownership validation, auto-expiring TTLs,
Lua-based safe release, and in-process fallback for fault tolerance.
"""

import asyncio
import uuid
from typing import Optional
from types import TracebackType

from core.config.logging import get_logger
from core.database.redis_client import get_redis
from core.database.redis_keys import key_lock, LOCK_DEFAULT_TTL

logger = get_logger("core.cache.distributed_lock")

# Lua script to release lock only if the token matches (atomic release)
_LUA_RELEASE_LOCK = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

# Process-level fallback lock map for when Redis is unavailable
_fallback_locks: dict[str, asyncio.Lock] = {}


class DistributedLock:
    """
    Async distributed lock using Redis with TTL and safe atomic release.

    Usage:
        async with DistributedLock("reminder_scheduler", ttl_seconds=30) as acquired:
            if acquired:
                await do_background_work()
    """

    def __init__(
        self,
        resource_name: str,
        ttl_seconds: int = LOCK_DEFAULT_TTL,
        timeout_seconds: float = 0.0,
    ) -> None:
        self.resource_name = resource_name
        self.lock_key = key_lock(resource_name)
        self.ttl_seconds = ttl_seconds
        self.timeout_seconds = timeout_seconds
        self.token = str(uuid.uuid4())
        self._acquired = False
        self._using_local_fallback = False

    async def acquire(self) -> bool:
        """
        Attempt to acquire the lock.
        Returns True if acquired, False otherwise.
        """
        ttl_ms = int(self.ttl_seconds * 1000)
        end_time = asyncio.get_event_loop().time() + self.timeout_seconds

        while True:
            try:
                redis = get_redis()
                # SET key token NX PX ttl_ms
                res = await redis.set(self.lock_key, self.token, nx=True, px=ttl_ms)
                if res:
                    self._acquired = True
                    return True
            except Exception as e:
                logger.debug(f"Redis unavailable for distributed lock '{self.lock_key}', using local fallback: {e}")
                # Fallback to in-process asyncio Lock
                if self.lock_key not in _fallback_locks:
                    _fallback_locks[self.lock_key] = asyncio.Lock()
                
                local_lock = _fallback_locks[self.lock_key]
                if not local_lock.locked():
                    await local_lock.acquire()
                    self._acquired = True
                    self._using_local_fallback = True
                    return True
                else:
                    self._acquired = False
                    return False

            if asyncio.get_event_loop().time() >= end_time:
                break
            await asyncio.sleep(0.1)

        self._acquired = False
        return False

    async def release(self) -> bool:
        """
        Release the lock safely if owned.
        """
        if not self._acquired:
            return False

        if self._using_local_fallback:
            local_lock = _fallback_locks.get(self.lock_key)
            if local_lock and local_lock.locked():
                try:
                    local_lock.release()
                except Exception:
                    pass
            self._acquired = False
            return True

        try:
            redis = get_redis()
            res = await redis.eval(_LUA_RELEASE_LOCK, 1, self.lock_key, self.token)
            self._acquired = False
            return bool(res)
        except Exception as e:
            logger.debug(f"Failed to release Redis lock '{self.lock_key}': {e}")
            self._acquired = False
            return False

    async def __aenter__(self) -> bool:
        return await self.acquire()

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.release()
