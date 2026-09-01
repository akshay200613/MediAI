"""
Request Context & Structured Logging Middleware.
Injects unique Request IDs, tracks request duration, binds contextual fields
to structlog contextvars, and records standard HTTP access logs.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    1. Extracts or generates a unique `X-Request-ID` header.
    2. Binds `request_id`, `client_ip`, `method`, and `path` to structlog contextvars.
    3. Calculates execution duration and attaches `X-Response-Time-Ms` header.
    4. Emits structured access logs on request completion.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Clear any leftover context from previous requests in this async task
        structlog.contextvars.clear_contextvars()

        # Extract existing X-Request-ID or generate new UUID4
        request_id = request.headers.get("X-Request-ID")
        if not request_id or not request_id.strip():
            request_id = str(uuid.uuid4())

        client_ip = request.client.host if request.client else "127.0.0.1"
        method = request.method
        path = request.url.path

        # Bind context variables for all downstream loggers in this request task
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            client_ip=client_ip,
            method=method,
            path=path,
        )

        start_time = time.perf_counter()
        logger = structlog.get_logger("http.access")

        try:
            response: Response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time-Ms"] = str(duration_ms)

            # Skip noisy polling endpoints like /metrics
            if path not in ("/metrics", "/favicon.ico"):
                logger.info(
                    "HTTP Request Completed",
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )

            return response
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "HTTP Request Unhandled Exception",
                error=str(exc),
                duration_ms=duration_ms,
                exc_info=True,
            )
            raise
