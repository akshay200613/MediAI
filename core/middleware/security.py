"""
Security Middleware for MediAI.
Includes:
1. SecurityHeadersMiddleware – sets HTTP security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, etc.)
2. RateLimitMiddleware – Redis sliding-window rate limiter.
   - /api/v1/auth/login    : 10 req / 60s  per IP
   - /api/v1/auth/register : 5 req / 60s   per IP
   - /api/v1/medai/chat    : 30 req / 60s  per IP  (DoS guard)
                             + 10 req / 60s per user_id (AI cost / fairness guard)
"""

import base64
import json
import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.config.settings import settings
from core.config.logging import get_logger
from core.database.redis_client import get_redis
from core.database.redis_keys import key_ratelimit

logger = get_logger("core.middleware.security")


# ─────────────────────────────────────────────────────────────────────────────
# SecurityHeadersMiddleware
# ─────────────────────────────────────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Applies security headers to every HTTP response:
    - X-Frame-Options: DENY (clickjacking protection)
    - X-Content-Type-Options: nosniff (MIME sniffing protection)
    - X-XSS-Protection: 1; mode=block (legacy XSS filter)
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: restricts sensitive browser features
    - Strict-Transport-Security: HSTS (enforced in production)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)

        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        return response


# ─────────────────────────────────────────────────────────────────────────────
# RateLimitMiddleware
# ─────────────────────────────────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Distributed Redis-backed sliding-window rate limiter.

    Two tiers for the AI chat endpoint:
      1. IP-level (30/min)  – broad DoS / bot guard.
      2. User-level (10/min) – per-authenticated-user AI cost & fairness guard.
         The user_id is read from the JWT payload without re-verifying the
         signature (actual auth still happens inside the route handler).

    Gracefully falls back to an in-memory sliding window when Redis is unreachable.
    """

    # (max_requests, window_seconds) keyed by path — IP-level guard
    IP_LIMITS: dict[str, tuple[int, int]] = {
        "/api/v1/auth/login": (10, 60),
        "/api/v1/auth/register": (5, 60),
        "/api/v1/medai/chat": (30, 60),
    }

    # Per-user limits for AI-intensive endpoints
    USER_LIMITS: dict[str, tuple[int, int]] = {
        "/api/v1/medai/chat": (10, 60),   # 10 messages / 60s per user
    }

    def __init__(self, app, **kwargs) -> None:
        super().__init__(app, **kwargs)
        # In-memory fallback: identifier -> path -> timestamps
        self._local: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _decode_user_id(request: Request) -> str | None:
        """
        Extract user_id from the JWT bearer token payload segment.
        Does NOT verify the signature — used solely for rate-limit key derivation.
        """
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth.split(" ", 1)[1].strip()
        try:
            parts = token.split(".")
            if len(parts) < 2:
                return None
            seg = parts[1]
            # Add padding so base64 decoder doesn't complain
            seg += "=" * (-len(seg) % 4)
            payload = json.loads(base64.urlsafe_b64decode(seg).decode("utf-8"))
            uid = payload.get("sub") or payload.get("user_id") or ""
            return str(uid) if uid else None
        except Exception:
            return None

    async def _sliding_window(
        self,
        scope: str,
        identifier: str,
        path: str,
        max_requests: int,
        window_seconds: int,
        now: float,
    ) -> tuple[bool, int]:
        """
        Run one sliding-window check.
        Returns (is_rate_limited, current_window_count).
        """
        cutoff = now - window_seconds
        try:
            redis = get_redis()
            rl_key = key_ratelimit(scope, identifier, path)

            pipe = redis.pipeline()
            pipe.zremrangebyscore(rl_key, 0, cutoff)                       # evict expired
            pipe.zadd(rl_key, {f"{now}:{time.perf_counter()}": now})       # add current
            pipe.zcard(rl_key)                                              # count in window
            pipe.expire(rl_key, window_seconds + 5)                        # auto-cleanup TTL

            results = await pipe.execute()
            count: int = results[2]
            return count > max_requests, count

        except Exception as exc:
            logger.debug(
                "Redis rate-limiter unavailable, using local fallback",
                scope=scope,
                identifier=identifier,
                path=path,
                error=str(exc),
            )
            # In-memory fallback
            ts_list = [t for t in self._local[identifier][path] if t > cutoff]
            limited = len(ts_list) >= max_requests
            if not limited:
                ts_list.append(now)
            self._local[identifier][path] = ts_list
            return limited, len(ts_list)

    def _rate_limit_response(
        self, message: str, window_seconds: int, scope: str, identifier: str, path: str, count: int, limit: int
    ) -> JSONResponse:
        logger.warning(
            "Rate limit exceeded",
            scope=scope,
            identifier=identifier,
            path=path,
            count=count,
            limit=limit,
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"success": False, "message": message, "data": None},
            headers={"Retry-After": str(window_seconds)},
        )

    # ── Main dispatch ─────────────────────────────────────────────────────────

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()

        # ── 1. IP-level guard ─────────────────────────────────────────────────
        if path in self.IP_LIMITS:
            max_req, window = self.IP_LIMITS[path]
            limited, count = await self._sliding_window("ip", client_ip, path, max_req, window, now)
            if limited:
                return self._rate_limit_response(
                    "Rate limit exceeded. Please wait a moment before trying again.",
                    window, "ip", client_ip, path, count, max_req,
                )

        # ── 2. Per-user guard (AI chat only) ──────────────────────────────────
        if path in self.USER_LIMITS:
            user_id = self._decode_user_id(request)
            if user_id:
                max_req_u, window_u = self.USER_LIMITS[path]
                limited_u, count_u = await self._sliding_window(
                    "user", user_id, path, max_req_u, window_u, now
                )
                if limited_u:
                    return self._rate_limit_response(
                        (
                            f"You have reached the limit of {max_req_u} AI chat messages "
                            "per minute. Please wait before sending another message."
                        ),
                        window_u, "user", user_id, path, count_u, max_req_u,
                    )

        return await call_next(request)
