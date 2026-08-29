"""
Shared pytest fixtures for MediAI test suite.

Provides:
- mock_session     unittest.mock AsyncMock mimicking AsyncSession
- admin_token      Bearer token string for admin role
- doctor_token     Bearer token string for doctor role
- patient_token    Bearer token string for patient role
- admin_headers    dict suitable for httpx headers
- test_app         FastAPI app with lifespan bypassed
- async_client     httpx.AsyncClient wired to the test app + mock DB
"""
# NOTE: asyncio_mode = "auto" is set in pyproject.toml [tool.pytest.ini_options].
# All async fixtures and tests are collected automatically without needing
# @pytest.mark.asyncio on every function.

import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import warnings

# Suppress pytest-asyncio legacy-mode deprecation noise
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pytest_asyncio")
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from core.auth.jwt_handler import create_access_token
from core.database.session import get_db


# ── JWT helpers ───────────────────────────────────────────────────────────────

def _make_token(role: str, user_id: str | None = None, email: str | None = None) -> str:
    uid = user_id or str(uuid.uuid4())
    mail = email or f"{role}@gmail.com"
    return create_access_token({"sub": uid, "email": mail, "role": role})


@pytest.fixture(scope="session")
def admin_user_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture(scope="session")
def doctor_user_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture(scope="session")
def patient_user_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture(scope="session")
def admin_token(admin_user_id: str) -> str:
    return _make_token("admin", user_id=admin_user_id, email="admin@gmail.com")


@pytest.fixture(scope="session")
def doctor_token(doctor_user_id: str) -> str:
    return _make_token("doctor", user_id=doctor_user_id, email="doctor@gmail.com")


@pytest.fixture(scope="session")
def patient_token(patient_user_id: str) -> str:
    return _make_token("patient", user_id=patient_user_id, email="patient@gmail.com")


@pytest.fixture(scope="session")
def admin_headers(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def doctor_headers(doctor_token: str) -> dict:
    return {"Authorization": f"Bearer {doctor_token}"}


@pytest.fixture(scope="session")
def patient_headers(patient_token: str) -> dict:
    return {"Authorization": f"Bearer {patient_token}"}


# ── Mock DB session ───────────────────────────────────────────────────────────

@pytest.fixture
def mock_session() -> AsyncMock:
    """Return a fully mocked AsyncSession for unit tests."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.first.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_result)
    session.close = AsyncMock()
    return session


# ── Test FastAPI application ──────────────────────────────────────────────────

def _build_test_app() -> FastAPI:
    """
    Build the FastAPI app WITHOUT triggering the real lifespan
    (no DB/Redis/Qdrant connections at startup).
    """
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        yield  # skip all startup/shutdown side-effects

    from fastapi.middleware.cors import CORSMiddleware
    from core.middleware.security import SecurityHeadersMiddleware, RateLimitMiddleware
    from core.api.v1.router import core_v1_router
    from domains.medai.registry import register as register_medai

    app = FastAPI(
        title="MedAI Test",
        version="0.0.0",
        lifespan=_noop_lifespan,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(core_v1_router)
    register_medai(app)
    return app


@pytest.fixture(scope="session")
def test_app() -> FastAPI:
    return _build_test_app()


@pytest.fixture
async def async_client(test_app: FastAPI, mock_session: AsyncMock) -> AsyncGenerator[AsyncClient, None]:  # noqa: RUF029
    """
    AsyncClient bound to test app.
    The real `get_db` dependency is overridden with the mock session so that
    no real database connection is required.

    Each test gets a fresh override so that mock_session can be reset per-test.
    """
    async def _override_get_db() -> AsyncGenerator:
        yield mock_session

    test_app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://testserver",
    ) as client:
        yield client
    test_app.dependency_overrides.pop(get_db, None)
