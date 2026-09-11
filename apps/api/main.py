"""
FastAPI Application Factory.
Wires together middleware, routers, domain registries, exception handlers, and lifespan events.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import structlog

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os

from core.config.settings import settings
from core.config.logging import configure_logging, get_logger
from core.database.base import engine, Base
from core.database.redis_client import get_redis_pool, close_redis_pool
from core.database.qdrant_client import close_qdrant_client
from core.api.v1.router import core_v1_router
from core.metrics import create_instrumentator, app_info, init_metrics, exceptions_total
from core.middleware.request_context import RequestContextMiddleware
from core.middleware.security import SecurityHeadersMiddleware, RateLimitMiddleware
from core.exceptions import MediAIException
from core.ai.llm.litellm_client import AIServiceUnavailableError

# ── Domain Registries ─────────────────────────────────────────────────────────
from domains.medai.registry import register as register_medai

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup → yield → shutdown."""
    import os
    # Startup
    configure_logging()
    logger.info("Starting MedAI", version=settings.app_version, env=settings.environment)

    # Pre-register zero-value metric series for Prometheus
    init_metrics()

    # Publish app metadata to Prometheus info metric
    app_info.info({
        "version": settings.app_version,
        "environment": settings.environment,
        "app_name": settings.app_name,
    })

    # Inject provider API keys into os.environ so litellm can find them
    if settings.gemini_api_key:
        os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
        os.environ["GOOGLE_API_KEY"] = settings.gemini_api_key
    if settings.groq_api_key:
        os.environ["GROQ_API_KEY"] = settings.groq_api_key

    # Force the LiteLLM Router singleton to rebuild with current settings.
    from core.ai.llm.litellm_client import reset_router
    reset_router()

    # Ensure DB tables exist (strictly for development; production schemas are managed by Alembic)
    if settings.is_development and not settings.is_production:
        logger.info("Development mode: verifying base tables (create_all)")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    else:
        logger.info("Production mode: table schema is managed strictly via Alembic migrations")

    # Pre-warm Redis pool
    get_redis_pool()
    logger.info("Redis pool initialized")

    # Start Distributed WebSocket Pub/Sub listener for multi-worker synchronization
    from domains.medai.websockets.manager import manager as ws_manager
    ws_manager.start_pubsub_listener()

    # Start Background Appointment Reminder Scheduler
    from domains.medai.services.reminder_scheduler import reminder_scheduler
    reminder_scheduler.start()

    logger.info("MedAI startup complete")
    yield

    # Shutdown
    logger.info("Shutting down MedAI")
    await reminder_scheduler.stop()
    await ws_manager.stop_pubsub_listener()
    await close_redis_pool()
    await close_qdrant_client()
    await engine.dispose()
    logger.info("MedAI shutdown complete")


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="MedAI – Intelligent Clinic Management System",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Middleware (Registered in order of execution: outer to inner) ───────────
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:[0-9]+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Structured Exception Handlers ──────────────────────────────────────────

    @app.exception_handler(MediAIException)
    async def handle_mediai_exception(request: Request, exc: MediAIException):
        req_id = request.headers.get("X-Request-ID") or structlog.contextvars.get_contextvars().get("request_id", "")
        exceptions_total.labels(exception_type=exc.__class__.__name__, status_code=str(exc.status_code)).inc()
        logger.warning(
            "Application Domain Exception",
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            request_id=req_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(request_id=req_id),
            headers={"X-Request-ID": req_id} if req_id else None,
        )

    @app.exception_handler(AIServiceUnavailableError)
    async def handle_ai_unavailable_error(request: Request, exc: AIServiceUnavailableError):
        req_id = request.headers.get("X-Request-ID") or structlog.contextvars.get_contextvars().get("request_id", "")
        exceptions_total.labels(exception_type="AIServiceUnavailableError", status_code="503").inc()
        logger.error(
            "AI Service Unavailable Exception",
            error=str(exc),
            status_code=503,
            request_id=req_id,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "error": {
                    "code": "AI_SERVICE_UNAVAILABLE",
                    "message": AIServiceUnavailableError.USER_MESSAGE,
                    "details": None,
                },
                "request_id": req_id,
            },
            headers={"X-Request-ID": req_id, "Retry-After": "10"} if req_id else {"Retry-After": "10"},
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException):
        req_id = request.headers.get("X-Request-ID") or structlog.contextvars.get_contextvars().get("request_id", "")
        exceptions_total.labels(exception_type="HTTPException", status_code=str(exc.status_code)).inc()
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail,
                    "details": None,
                },
                "request_id": req_id,
            },
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        req_id = request.headers.get("X-Request-ID") or structlog.contextvars.get_contextvars().get("request_id", "")
        exceptions_total.labels(exception_type="RequestValidationError", status_code="422").inc()
        logger.warning("Request validation failed", errors=exc.errors(), request_id=req_id)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request payload or parameters",
                    "details": exc.errors(),
                },
                "request_id": req_id,
            },
            headers={"X-Request-ID": req_id} if req_id else None,
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(request: Request, exc: Exception):
        req_id = request.headers.get("X-Request-ID") or structlog.contextvars.get_contextvars().get("request_id", "")
        exceptions_total.labels(exception_type=exc.__class__.__name__, status_code="500").inc()
        logger.error(
            "Unhandled Server Exception",
            path=request.url.path,
            error=str(exc),
            exc_info=True,
            request_id=req_id,
        )
        msg = "An internal error occurred. Please try again later." if settings.is_production else f"Internal Server Error: {str(exc)}"
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": msg,
                    "details": None,
                },
                "request_id": req_id,
            },
            headers={"X-Request-ID": req_id} if req_id else None,
        )

    # ── Core Routes ───────────────────────────────────────────────────────────
    app.include_router(core_v1_router)

    # ── Domain Registration ───────────────────────────────────────────────────
    register_medai(app)
    
    # ── Static Files ──────────────────────────────────────────────────────────
    os.makedirs("uploads", exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

    # ── Prometheus Metrics ────────────────────────────────────────────────────
    # Instrument AFTER all routers are registered so all routes are captured.
    # Exposes GET /metrics in Prometheus text format.
    instrumentator = create_instrumentator()
    instrumentator.instrument(app).expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
        tags=["Monitoring"],
    )

    logger.info("Application factory complete")
    return app


app = create_app()
