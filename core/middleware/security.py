"""
Security Middleware for MediAI.
Includes:
1. SecurityHeadersMiddleware – sets HTTP security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, etc.)
2. RateLimitMiddleware – simple in-memory sliding-window rate limiter for sensitive routes (Auth, Chat)
"""

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


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Distributed Redis-backed sliding-window rate limiter for sensitive endpoints:
    - /api/v1/auth/login    : max 10 requests per minute per IP
    - /api/v1/auth/register : max 5 requests per minute per IP
    - /api/v1/medai/chat    : max 30 requests per minute per IP

    Gracefully falls back to bounded in-memory sliding window when Redis is unreachable.
    """

    RATE_LIMITS: dict[str, tuple[int, int]] = {
        "/api/v1/auth/login": (10, 60),     # 10 req / 60s
        "/api/v1/auth/register": (5, 60),   # 5 req / 60s
        "/api/v1/medai/chat": (30, 60),     # 30 req / 60s
    }

    def __init__(self, app, **kwargs) -> None:
        super().__init__(app, **kwargs)
        # In-memory fallback tracking: ip -> path -> list of request timestamps
        self._local_fallback: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        client_ip = request.client.host if request.client else "127.0.0.1"

        if path in self.RATE_LIMITS:
            max_requests, window_seconds = self.RATE_LIMITS[path]
            now = time.time()
            cutoff = now - window_seconds
            is_limited = False
            current_count = 0

            # 1. Attempt distributed rate check via Redis sliding window (Sorted Set)
            try:
                redis = get_redis()
                rl_key = key_ratelimit("ip", client_ip, path)
                
                pipe = redis.pipeline()
                # Remove timestamps older than the sliding window
                pipe.zremrangebyscore(rl_key, 0, cutoff)
                # Add current request timestamp (using timestamp as score and unique string as member)
                member = f"{now}:{time.perf_counter()}"
                pipe.zadd(rl_key, {member: now})
                # Count current active entries in the window
                pipe.zcard(rl_key)
                # Set TTL to slightly longer than window for automatic cleanup
                pipe.expire(rl_key, window_seconds + 5)
                
                results = await pipe.execute()
                current_count = results[2]
                if current_count > max_requests:
                    is_limited = True
            except Exception as e:
                # 2. Resilient fallback to local bounded in-memory sliding window
                logger.debug(
                    "Redis rate-limiter unavailable, utilizing local fallback",
                    ip=client_ip,
                    path=path,
                    error=str(e),
                )
                timestamps = [t for t in self._local_fallback[client_ip][path] if t > cutoff]
                if len(timestamps) >= max_requests:
                    is_limited = True
                    current_count = len(timestamps)
                else:
                    timestamps.append(now)
                self._local_fallback[client_ip][path] = timestamps

            if is_limited:
                logger.warning(
                    "Rate limit exceeded",
                    ip=client_ip,
                    path=path,
                    count=current_count,
                    max_allowed=max_requests,
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "success": False,
                        "message": "Rate limit exceeded. Please wait a moment before trying again.",
                        "data": None,
                    },
                    headers={"Retry-After": str(window_seconds)},
                )

        return await call_next(request)

