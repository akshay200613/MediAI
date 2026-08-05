"""
Integration tests for auth API endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "password": "securepass123",
        "full_name": "New User",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert "id" in data["data"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    payload = {
        "email": "duplicate@example.com",
        "password": "securepass123",
        "full_name": "Dup User",
    }
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json={
        "email": "logintest@example.com",
        "password": "mypassword123",
        "full_name": "Login Test",
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "logintest@example.com",
        "password": "mypassword123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/login", json={
        "email": "logintest@example.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data
