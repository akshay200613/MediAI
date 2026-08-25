"""
Integration tests for core/api/v1/auth.py endpoints.

Uses the test FastAPI app + mock DB session (no real PostgreSQL).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from core.auth.jwt_handler import create_refresh_token, hash_password


def _mock_user(
    role: str = "patient",
    email: str = "test@medai.com",
    is_active: bool = True,
    is_verified: bool = True,
    password: str = "Password123!",
) -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = email
    user.role = role
    user.full_name = "Test User"
    user.domain = "medai"
    user.is_active = is_active
    user.is_verified = is_verified
    user.hashed_password = hash_password(password)
    return user


# ── POST /api/v1/auth/login ───────────────────────────────────────────────────

class TestLogin:
    async def test_login_with_valid_credentials_returns_tokens(
        self, async_client: AsyncClient, mock_session: AsyncMock
    ):
        user = _mock_user()

        # Patch the repo lookup used inside the login endpoint
        with patch(
            "core.repositories.base_repository.BaseRepository.get_by_field",
            new=AsyncMock(return_value=user),
        ):
            resp = await async_client.post(
                "/api/v1/auth/login",
                json={"email": user.email, "password": "Password123!"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "access_token" in body["data"]
        assert "refresh_token" in body["data"]

    async def test_login_with_wrong_password_returns_401(
        self, async_client: AsyncClient, mock_session: AsyncMock
    ):
        user = _mock_user()

        with patch(
            "core.repositories.base_repository.BaseRepository.get_by_field",
            new=AsyncMock(return_value=user),
        ):
            resp = await async_client.post(
                "/api/v1/auth/login",
                json={"email": user.email, "password": "WrongPassword!"},
            )

        assert resp.status_code == 401

    async def test_login_with_unknown_email_returns_401(
        self, async_client: AsyncClient, mock_session: AsyncMock
    ):
        with patch(
            "core.repositories.base_repository.BaseRepository.get_by_field",
            new=AsyncMock(return_value=None),
        ):
            resp = await async_client.post(
                "/api/v1/auth/login",
                json={"email": "nobody@nowhere.com", "password": "anything"},
            )

        assert resp.status_code == 401

    async def test_login_with_disabled_account_returns_403(
        self, async_client: AsyncClient, mock_session: AsyncMock
    ):
        user = _mock_user(is_active=False)

        with patch(
            "core.repositories.base_repository.BaseRepository.get_by_field",
            new=AsyncMock(return_value=user),
        ):
            resp = await async_client.post(
                "/api/v1/auth/login",
                json={"email": user.email, "password": "Password123!"},
            )

        assert resp.status_code == 403


# ── POST /api/v1/auth/refresh ─────────────────────────────────────────────────

class TestRefreshToken:
    async def test_valid_refresh_token_returns_new_tokens(
        self, async_client: AsyncClient
    ):
        refresh_token = create_refresh_token(
            {"sub": str(uuid.uuid4()), "email": "u@test.com", "role": "patient"}
        )
        resp = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body["data"]

    async def test_invalid_refresh_token_returns_401(
        self, async_client: AsyncClient
    ):
        resp = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "this.is.not.a.valid.token"},
        )
        assert resp.status_code == 401

    async def test_access_token_as_refresh_returns_401(
        self, async_client: AsyncClient, admin_token: str
    ):
        """Using an access token where a refresh token is expected should fail."""
        resp = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": admin_token},
        )
        assert resp.status_code == 401


# ── GET /api/v1/auth/me ───────────────────────────────────────────────────────

class TestGetMe:
    async def test_me_without_token_returns_401(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/auth/me")
        assert resp.status_code == 401 or resp.status_code == 403

    async def test_me_with_valid_admin_token(
        self, async_client: AsyncClient, admin_headers: dict, mock_session: AsyncMock
    ):
        user = _mock_user(role="admin", email="admin@medai.test")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        with patch(
            "core.repositories.base_repository.BaseRepository.get_by_id",
            new=AsyncMock(return_value=user),
        ):
            mock_session.execute = AsyncMock(return_value=mock_result)
            resp = await async_client.get("/api/v1/auth/me", headers=admin_headers)

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["role"] == "admin"
