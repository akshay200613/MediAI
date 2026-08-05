"""
Rate Limiting Middleware – Redis-backed sliding window rate limiter.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from core.database.redis_client import get_redis
from core.config.settings import settings


RATE_LIMIT_REQUESTS = 100   # requests
RATE_LIMIT_WINDOW = 60      # seconds


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter.
    Limits to RATE_LIMIT_REQUESTS per RATE_LIMIT_WINDOW seconds per IP.
    Skipped entirely in development mode.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if settings.is_development:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        redis = get_redis()
        key = f"rate_limit:{client_ip}"

        try:
            current = await redis.incr(key)
            if current == 1:
                await redis.expire(key, RATE_LIMIT_WINDOW)

            if current > RATE_LIMIT_REQUESTS:
                return JSONResponse(
                    status_code=429,
                    content={"success": False, "message": "Too many requests. Please slow down."},
                    headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
                )
        except Exception:
            # Don't block requests if Redis is unavailable
            pass

        return await call_next(request)
