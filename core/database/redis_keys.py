"""
Redis Key Namespaces and Constants for MediAI.
Enforces consistent hierarchical namespacing, key formatting, and TTL definitions
across distributed caching, rate-limiting, authentication, locking, and Pub/Sub.
"""

import hashlib

# ── Prefix & Namespaces ───────────────────────────────────────────────────────
PREFIX = "medai"

NS_AUTH = f"{PREFIX}:auth"
NS_CACHE = f"{PREFIX}:cache"
NS_RATELIMIT = f"{PREFIX}:ratelimit"
NS_LOCK = f"{PREFIX}:lock"
NS_WS = f"{PREFIX}:ws"
NS_SESSION = f"{PREFIX}:session"

# ── Pub/Sub Channels ──────────────────────────────────────────────────────────
WS_BROADCAST_CHANNEL = f"{NS_WS}:broadcast"

# ── TTLs (seconds) ────────────────────────────────────────────────────────────
DEFAULT_CACHE_TTL = 300            # 5 minutes
SHORT_CACHE_TTL = 60               # 1 minute
LONG_CACHE_TTL = 3600              # 1 hour
DAY_CACHE_TTL = 86400              # 24 hours
PASSWORD_RESET_TTL = 86400 * 3     # 3 days max pending before expiry
DEFAULT_TOKEN_EXPIRY = 86400 * 7   # 7 days default
LOCK_DEFAULT_TTL = 60              # 60 seconds distributed lock TTL


def hash_token(token: str) -> str:
    """Hash a token with SHA-256 for compact and safe Redis key storage."""
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


def key_revoked_token(token_or_hash: str) -> str:
    """Namespace key for revoked JWTs."""
    # If the string is already a 64-char hex sha256, use directly, else hash it
    h = token_or_hash if len(token_or_hash) == 64 and all(c in "0123456789abcdefABCDEF" for c in token_or_hash) else hash_token(token_or_hash)
    return f"{NS_AUTH}:revoked_token:{h}"


def key_pending_reset_user(user_id: str) -> str:
    """Namespace key for individual pending password reset request."""
    return f"{NS_AUTH}:pending_reset:{user_id}"


def key_pending_reset_index() -> str:
    """Namespace set key for indexing all active pending password reset user IDs."""
    return f"{NS_AUTH}:pending_resets_set"


def key_ratelimit(scope: str, identifier: str, endpoint: str) -> str:
    """Namespace key for sliding window rate limiter."""
    clean_endpoint = endpoint.replace("/", "_").strip("_")
    return f"{NS_RATELIMIT}:{scope}:{identifier}:{clean_endpoint}"


def key_lock(resource_name: str) -> str:
    """Namespace key for distributed locks."""
    return f"{NS_LOCK}:{resource_name}"


def key_cache(domain: str, identifier: str) -> str:
    """Namespace key for distributed domain cache."""
    return f"{NS_CACHE}:{domain}:{identifier}"
