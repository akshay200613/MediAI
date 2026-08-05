"""
Pytest configuration and shared fixtures.
"""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.database.base import Base
from apps.api.main import app
from core.database.session import get_db

# ── Test Database ─────────────────────────────────────────────────────────────
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:testpass@localhost:5432/ai_serviceos_test"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Create all tables for the test session, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session with rollback after each test."""
    async with test_engine.begin() as conn:
        async with AsyncSession(bind=conn) as session:
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTP test client with overridden DB session."""
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register and login a test user, return auth headers."""
    # Register
    await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User",
    })

    # Login
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword123",
    })
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
