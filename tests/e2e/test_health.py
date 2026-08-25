"""
E2E tests for /health endpoint.
These verify the health route responds correctly even when services are mocked.
"""

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    async def test_health_returns_200(self, async_client: AsyncClient):
        """Health endpoint must always return 200 even when external services are down."""
        resp = await async_client.get("/api/v1/health")
        assert resp.status_code == 200

    async def test_health_response_has_status_field(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/health")
        body = resp.json()
        assert "status" in body
        assert body["status"] in ("healthy", "degraded")

    async def test_health_response_has_version_field(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/health")
        body = resp.json()
        assert "version" in body

    async def test_health_response_has_services_field(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/health")
        body = resp.json()
        assert "services" in body
        assert isinstance(body["services"], dict)

    async def test_health_response_has_timestamp(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/health")
        body = resp.json()
        assert "timestamp" in body
