"""
Token Blacklist Service.
Provides distributed JWT token revocation using Redis with SHA-256 key hashing,
exact JWT exp TTL calculation, and in-memory fallback for worker safety.
"""

import time
from jose import jwt

from core.config.logging import get_logger
from core.database.redis_client import get_redis
from core.database.redis_keys import key_revoked_token, hash_token, DEFAULT_TOKEN_EXPIRY

logger = get_logger("core.auth.token_blacklist")

# Fallback local in-memory store: token_hash -> expiration timestamp
_in_memory_blacklist: dict[str, float] = {}


def _clean_expired_local() -> None:
    now = time.time()
    expired = [k for k, exp in _in_memory_blacklist.items() if exp <= now]
    for k in expired:
        _in_memory_blacklist.pop(k, None)


def _get_token_remaining_ttl(token: str, default_ttl: int = DEFAULT_TOKEN_EXPIRY) -> int:
    """Calculate remaining seconds until token's 'exp' claim."""
    try:
        # Extract unverified claims to read 'exp'
        unverified = jwt.get_unverified_claims(token)
        exp = unverified.get("exp")
        if exp:
            remaining = int(exp - time.time())
            return max(1, remaining)
    except Exception:
        pass
    return default_ttl


async def blacklist_token(token: str, expires_in_seconds: int | None = None) -> None:
    """
    Revoke a JWT token by adding its SHA-256 hash to Redis until its expiration.
    """
    if not token or not token.strip():
        return

    ttl = expires_in_seconds if expires_in_seconds is not None else _get_token_remaining_ttl(token)
    token_h = hash_token(token)
    redis_key = key_revoked_token(token_h)

    # In-memory fallback
    _in_memory_blacklist[token_h] = time.time() + ttl

    # Distributed Redis store
    try:
        redis = get_redis()
        await redis.setex(redis_key, ttl, "revoked")
        logger.info("JWT token revoked successfully", token_hash=token_h[:12], ttl_seconds=ttl)
    except Exception as e:
        logger.debug(f"Redis unavailable for token revocation, retained in local fallback: {e}")


async def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token has been revoked in Redis or local fallback.
    """
    if not token or not token.strip():
        return False

    token_h = hash_token(token)
    redis_key = key_revoked_token(token_h)

    # Check local fallback
    now = time.time()
    if token_h in _in_memory_blacklist:
        if _in_memory_blacklist[token_h] > now:
            return True
        else:
            _in_memory_blacklist.pop(token_h, None)

    # Check Redis
    try:
        redis = get_redis()
        val = await redis.get(redis_key)
        return val is not None
    except Exception as e:
        logger.debug(f"Redis unavailable for token blacklist check: {e}")
        _clean_expired_local()
        return token_h in _in_memory_blacklist
