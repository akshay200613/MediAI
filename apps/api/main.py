"""
FastAPI Application Factory.
Wires together middleware, routers, domain registries, and lifespan events.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse

from core.config.settings import settings
from core.config.logging import configure_logging, get_logger
from core.database.base import engine, Base
from core.database.redis_client import get_redis_pool, close_redis_pool
from core.database.qdrant_client import close_qdrant_client
from core.api.v1.router import core_v1_router
from core.metrics import create_instrumentator, app_info, init_metrics
from core.middleware.security import SecurityHeadersMiddleware, RateLimitMiddleware

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

    # ── Security & CORS Middleware ────────────────────────────────────────────
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

    # ── Global Exception Handler ──────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled Exception", path=request.url.path, error=str(exc), exc_info=True)
        if settings.is_production:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "An internal error occurred. Please try again later.",
                    "data": None,
                },
            )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Internal Server Error: {str(exc)}",
                "data": None,
            },
        )

    # ── Core Routes ───────────────────────────────────────────────────────────
    app.include_router(core_v1_router)

    # ── Domain Registration ───────────────────────────────────────────────────
    register_medai(app)

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
