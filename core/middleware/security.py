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
    Sliding-window rate limiter for sensitive endpoints:
    - /api/v1/auth/login    : max 10 requests per minute per IP
    - /api/v1/auth/register : max 5 requests per minute per IP
    - /api/v1/medai/chat    : max 30 requests per minute per IP
    """

    RATE_LIMITS: dict[str, tuple[int, int]] = {
        "/api/v1/auth/login": (10, 60),     # 10 req / 60s
        "/api/v1/auth/register": (5, 60),   # 5 req / 60s
        "/api/v1/medai/chat": (30, 60),     # 30 req / 60s
    }

    def __init__(self, app, **kwargs) -> None:
        super().__init__(app, **kwargs)
        # ip -> path -> list of request timestamps
        self._requests: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        client_ip = request.client.host if request.client else "127.0.0.1"

        if path in self.RATE_LIMITS:
            max_requests, window_seconds = self.RATE_LIMITS[path]
            now = time.time()
            cutoff = now - window_seconds

            # Filter out expired timestamps
            timestamps = [t for t in self._requests[client_ip][path] if t > cutoff]
            self._requests[client_ip][path] = timestamps

            if len(timestamps) >= max_requests:
                logger.warning(
                    "Rate limit exceeded",
                    ip=client_ip,
                    path=path,
                    count=len(timestamps),
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

            self._requests[client_ip][path].append(now)

        return await call_next(request)
