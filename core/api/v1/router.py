"""
Core API v1 Router – health, auth, and user endpoints.
"""

from fastapi import APIRouter

from core.api.v1.health import router as health_router
from core.api.v1.auth import router as auth_router
from core.config.constants import API_V1_PREFIX

core_v1_router = APIRouter(prefix=API_V1_PREFIX)
core_v1_router.include_router(health_router, prefix="/health", tags=["Health"])
core_v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
