"""
Token Blacklist Service.
Provides distributed token revocation using Redis with an in-memory fallback.
"""

import time
import logging
from core.database.redis_client import get_redis
from core.config.logging import get_logger

logger = get_logger(__name__)

# Fallback local in-memory store: token -> expiration timestamp
_in_memory_blacklist: dict[str, float] = {}


async def blacklist_token(token: str, expires_in_seconds: int = 86400 * 7) -> None:
    """
    Revoke a JWT token by adding it to the blacklist until its expiration.
    """
    if not token:
        return

    # In-memory store
    _in_memory_blacklist[token] = time.time() + expires_in_seconds

    # Redis store
    try:
        redis = get_redis()
        await redis.setex(f"blacklist:token:{token}", expires_in_seconds, "revoked")
    except Exception as e:
        logger.debug(f"Redis unavailable for token blacklisting, using in-memory store: {e}")


async def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token has been revoked.
    """
    if not token:
        return False

    # Check in-memory store
    now = time.time()
    if token in _in_memory_blacklist:
        if _in_memory_blacklist[token] > now:
            return True
        else:
            del _in_memory_blacklist[token]

    # Check Redis
    try:
        redis = get_redis()
        val = await redis.get(f"blacklist:token:{token}")
        return val is not None
    except Exception as e:
        logger.debug(f"Redis unavailable for token blacklist check: {e}")
        return False
