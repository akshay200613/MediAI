"""
Password Reset State Manager.
Provides distributed tracking for pending password reset requests across workers
using Redis with automatic TTL expiration and in-memory fallback.
Eliminates reliance on process-local global variables.
"""

import json
import time
from typing import Any

from core.config.logging import get_logger
from core.database.redis_client import get_redis
from core.database.redis_keys import (
    key_pending_reset_user,
    key_pending_reset_index,
    PASSWORD_RESET_TTL,
)

logger = get_logger("core.services.password_reset_service")


class PasswordResetStateManager:
    """
    Worker-safe, distributed manager for tracking pending password reset requests.
    """

    def __init__(self, default_ttl: int = PASSWORD_RESET_TTL) -> None:
        self.default_ttl = default_ttl
        # Local fallback: user_id -> (metadata_dict, expiry_timestamp)
        self._local_fallback: dict[str, tuple[dict[str, Any], float]] = {}

    def _clean_expired_local(self) -> None:
        now = time.time()
        expired = [uid for uid, (_, exp) in self._local_fallback.items() if exp <= now]
        for uid in expired:
            self._local_fallback.pop(uid, None)

    async def mark_pending(
        self,
        user_id: str,
        email: str,
        full_name: str,
        role: str = "user",
        ttl_seconds: int | None = None,
    ) -> None:
        """Mark a user as having a pending password reset request."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        uid_str = str(user_id)
        metadata = {
            "user_id": uid_str,
            "email": email,
            "full_name": full_name,
            "role": role,
            "requested_at": time.time(),
        }

        # Update local fallback
        self._local_fallback[uid_str] = (metadata, time.time() + ttl)

        try:
            redis = get_redis()
            user_key = key_pending_reset_user(uid_str)
            index_key = key_pending_reset_index()

            pipe = redis.pipeline()
            pipe.setex(user_key, ttl, json.dumps(metadata))
            pipe.sadd(index_key, uid_str)
            await pipe.execute()
            logger.info("Marked password reset request as pending", user_id=uid_str, email=email)
        except Exception as e:
            logger.debug(f"Redis unavailable for password reset state, stored in local fallback: {e}")

    async def is_pending(self, user_id: str) -> bool:
        """Check if a user has a pending password reset request."""
        uid_str = str(user_id)

        try:
            redis = get_redis()
            user_key = key_pending_reset_user(uid_str)
            exists = await redis.exists(user_key)
            if exists:
                return True
            else:
                # Clean up index if individual key expired
                index_key = key_pending_reset_index()
                await redis.srem(index_key, uid_str)
                return False
        except Exception as e:
            logger.debug(f"Redis unavailable for pending reset check, checking local fallback: {e}")
            self._clean_expired_local()
            return uid_str in self._local_fallback

    async def clear_pending(self, user_id: str) -> None:
        """Clear the pending password reset status upon admin approval."""
        uid_str = str(user_id)
        self._local_fallback.pop(uid_str, None)

        try:
            redis = get_redis()
            user_key = key_pending_reset_user(uid_str)
            index_key = key_pending_reset_index()

            pipe = redis.pipeline()
            pipe.delete(user_key)
            pipe.srem(index_key, uid_str)
            await pipe.execute()
            logger.info("Cleared pending password reset request", user_id=uid_str)
        except Exception as e:
            logger.debug(f"Redis unavailable for clear pending reset: {e}")

    async def list_pending_user_ids(self) -> list[str]:
        """Return all user IDs currently having active pending password reset requests."""
        active_ids: list[str] = []

        try:
            redis = get_redis()
            index_key = key_pending_reset_index()
            all_ids = await redis.smembers(index_key)

            for uid in all_ids:
                user_key = key_pending_reset_user(uid)
                if await redis.exists(user_key):
                    active_ids.append(uid)
                else:
                    # Clean up expired index member
                    await redis.srem(index_key, uid)
            return active_ids
        except Exception as e:
            logger.debug(f"Redis unavailable for list pending resets, using local fallback: {e}")
            self._clean_expired_local()
            return list(self._local_fallback.keys())


# Global singleton instance
password_reset_state = PasswordResetStateManager()
