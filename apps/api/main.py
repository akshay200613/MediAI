"""
FastAPI Application Factory.
Wires together middleware, routers, domain registries, and lifespan events.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config.settings import settings
from core.config.logging import configure_logging, get_logger
from core.database.base import engine, Base
from core.database.redis_client import get_redis_pool, close_redis_pool
from core.database.qdrant_client import close_qdrant_client
from core.api.v1.router import core_v1_router

# ── Domain Registries ─────────────────────────────────────────────────────────
from domains.medai.registry import register as register_medai

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup → yield → shutdown."""
    # Startup
    configure_logging()
    logger.info("Starting MedAI", version=settings.app_version, env=settings.environment)

    # Ensure DB tables exist (for dev; use Alembic in prod)
    if settings.is_development:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Pre-warm Redis pool
    get_redis_pool()
    logger.info("Redis pool initialized")

    logger.info("MedAI startup complete")
    yield

    # Shutdown
    logger.info("Shutting down MedAI")
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

    # ── Middleware ────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Core Routes ───────────────────────────────────────────────────────────
    app.include_router(core_v1_router)

    # ── Domain Registration ───────────────────────────────────────────────────
    register_medai(app)

    logger.info("Application factory complete")
    return app


app = create_app()
