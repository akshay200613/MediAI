"""
MedAI Domain Registry.
Registers all MedAI routes into the core app.
This is the ONLY file that the core platform imports from this domain.
"""

from fastapi import FastAPI

from core.config.logging import get_logger

logger = get_logger("medai.registry")


def register(app: FastAPI) -> None:
    """
    Register MedAI domain into the FastAPI app.
    Called once at startup from apps/api/main.py.
    """
    from domains.medai.api.v1.router import medai_v1_router

    # Register API routes
    app.include_router(medai_v1_router)
    logger.info("MedAI routes registered")
    logger.info("MedAI domain registration complete")
