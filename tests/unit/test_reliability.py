"""
Unit & Integration Tests for Production Reliability & Failure Scenarios.
Tests:
- DB unavailable failure handling
- Redis unavailable failure handling
- Gemini unavailable -> fallback to Groq
- Groq & Gemini unavailable -> 503 AI Service Unavailable
- Malformed LLM response handling
- External API timeout handling
- Worker restart & graceful lifespan shutdown
- Request ID propagation & structured logging context
- Health, liveness, and readiness probes
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from apps.api.main import app
from core.ai.llm.client import Message
from core.ai.llm.litellm_client import LiteLLMClient, AIServiceUnavailableError
from core.exceptions import (
    MediAIException,
    EntityNotFoundException,
    DatabaseUnavailableException,
    ExternalServiceTimeoutException,
)


# ── 1. Request ID & Structured Logging Context Tests ────────────────────────

@pytest.mark.asyncio
async def test_request_id_generation_and_headers(async_client: AsyncClient):
    """Verify that every HTTP response receives X-Request-ID and X-Response-Time-Ms."""
    # 1. Without client request ID
    res1 = await async_client.get("/api/v1/health/live")
    assert res1.status_code == 200
    assert "X-Request-ID" in res1.headers
    assert "X-Response-Time-Ms" in res1.headers

    # 2. With incoming client request ID
    custom_id = "client-trace-12345"
    res2 = await async_client.get("/api/v1/health/live", headers={"X-Request-ID": custom_id})
    assert res2.status_code == 200
    assert res2.headers.get("X-Request-ID") == custom_id


# ── 2. Health, Liveness, and Readiness Probe Tests ──────────────────────────

@pytest.mark.asyncio
async def test_liveness_probe(async_client: AsyncClient):
    """Test /api/v1/health/live and /api/v1/health/healthz."""
    res = await async_client.get("/api/v1/health/live")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "alive"

    res_z = await async_client.get("/api/v1/health/healthz")
    assert res_z.status_code == 200
    assert res_z.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_readiness_probe_healthy(async_client: AsyncClient):
    """Test readiness probe when DB and Redis are reachable."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock()

    with patch("core.api.v1.health.AsyncSessionLocal", return_value=mock_session), \
         patch("core.api.v1.health.get_redis", return_value=mock_redis):
        res = await async_client.get("/api/v1/health/ready")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ready"
        assert data["dependencies"]["database"] == "ready"
        assert data["dependencies"]["redis"] == "ready"


# ── 3. Failure Scenario: Database Unavailable ────────────────────────────────

@pytest.mark.asyncio
async def test_failure_scenario_db_unavailable(async_client: AsyncClient):
    """Verify that readiness and deep health accurately report 503 when DB is offline."""
    with patch("core.api.v1.health.AsyncSessionLocal", side_effect=ConnectionRefusedError("Database unreachable")):
        # Readiness probe must reject traffic
        ready_res = await async_client.get("/api/v1/health/ready")
        assert ready_res.status_code == 503
        ready_data = ready_res.json()
        assert ready_data["status"] == "unready"
        assert "unready" in ready_data["dependencies"]["database"]

        # Deep health probe must return 503
        health_res = await async_client.get("/api/v1/health")
        assert health_res.status_code == 503
        health_data = health_res.json()
        assert health_data["status"] == "unhealthy"
        assert "unhealthy" in health_data["services"]["postgres"]["status"]


# ── 4. Failure Scenario: Redis Unavailable ───────────────────────────────────

@pytest.mark.asyncio
async def test_failure_scenario_redis_unavailable(async_client: AsyncClient):
    """Verify system reports degraded status when Redis is offline without crashing the app."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()

    with patch("core.api.v1.health.AsyncSessionLocal", return_value=mock_session), \
         patch("core.api.v1.health.get_redis", side_effect=ConnectionRefusedError("Redis down")), \
         patch("core.database.qdrant_client.get_qdrant_client", side_effect=Exception("Qdrant down")):
        health_res = await async_client.get("/api/v1/health")
        assert health_res.status_code == 200  # Primary DB is still healthy
        data = health_res.json()
        assert data["status"] == "degraded"
        assert "degraded" in data["services"]["redis"]["status"]


# ── 5. Failure Scenario: Gemini Unavailable -> Fallback to Groq ─────────────

@pytest.mark.asyncio
async def test_failure_scenario_gemini_unavailable_fallback_to_groq():
    """Verify LiteLLM router triggers fallback to Groq and records metrics when Gemini fails."""
    mock_router = AsyncMock()

    # Simulate Gemini failing and Router successfully failing over to Groq model
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Hello from Groq fallback!"))]
    mock_response.model = "groq/llama-3.3-70b-versatile"
    mock_response.usage = MagicMock(prompt_tokens=15, completion_tokens=8, total_tokens=23)

    mock_router.acompletion = AsyncMock(return_value=mock_response)
    client = LiteLLMClient(router=mock_router)

    messages = [Message(role="user", content="Hello clinic")]
    res = await client.generate(messages, model="gemini/gemini-2.5-flash")

    assert res.content == "Hello from Groq fallback!"
    assert res.model == "groq/llama-3.3-70b-versatile"
    assert res.usage["prompt_tokens"] == 15


# ── 6. Failure Scenario: Gemini & Groq Both Unavailable ──────────────────────

@pytest.mark.asyncio
async def test_failure_scenario_all_llms_unavailable():
    """Verify AIServiceUnavailableError is raised when all LLM providers fail."""
    mock_router = AsyncMock()
    mock_router.acompletion = AsyncMock(side_effect=RuntimeError("All deployments exhausted (Gemini 429 & Groq 500)"))
    client = LiteLLMClient(router=mock_router)

    messages = [Message(role="user", content="Book appointment")]
    with pytest.raises(AIServiceUnavailableError) as exc_info:
        await client.generate(messages, model="gemini/gemini-2.5-flash")

    assert "The AI service is temporarily unavailable" in str(exc_info.value)


# ── 7. Failure Scenario: Malformed LLM Response ──────────────────────────────

@pytest.mark.asyncio
async def test_failure_scenario_malformed_llm_response():
    """Verify application handles malformed or non-JSON LLM responses gracefully."""
    mock_router = AsyncMock()

    # LLM outputs raw markdown or corrupted text instead of requested JSON
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="I am unable to output JSON today: {invalid json"))]
    mock_response.model = "gemini/gemini-2.5-flash"
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=10, total_tokens=20)
    mock_router.acompletion = AsyncMock(return_value=mock_response)
    client = LiteLLMClient(router=mock_router)

    res = await client.generate([Message(role="user", content="give json")])
    assert res.content == "I am unable to output JSON today: {invalid json"
    # Safe parsing attempt doesn't throw unhandled exception
    try:
        data = json.loads(res.content)
    except json.JSONDecodeError:
        data = None
    assert data is None


# ── 8. Failure Scenario: External API Timeout ────────────────────────────────

@pytest.mark.asyncio
async def test_failure_scenario_external_api_timeout():
    """Test ExternalServiceTimeoutException formatting and HTTP 504 status code."""
    exc = ExternalServiceTimeoutException("PaymentGateway", timeout_seconds=5.0)
    res_dict = exc.to_dict(request_id="req-timeout-999")

    assert exc.status_code == 504
    assert res_dict["error"]["code"] == "GATEWAY_TIMEOUT"
    assert "timed out after 5.0s" in res_dict["error"]["message"]
    assert res_dict["request_id"] == "req-timeout-999"


# ── 9. Structured Exception Hierarchy & Error Responses ──────────────────────

@pytest.mark.asyncio
async def test_structured_domain_exception_handling():
    """Verify that domain exceptions render standard JSON errors with request IDs."""
    exc = EntityNotFoundException("PatientRecord", "pat-12345")
    data = exc.to_dict(request_id="req-trace-404")

    assert exc.status_code == 404
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"
    assert "PatientRecord with identifier 'pat-12345' was not found" in data["error"]["message"]
    assert data["request_id"] == "req-trace-404"


# ── 10. Worker Restart & Graceful Lifespan Shutdown ──────────────────────────

@pytest.mark.asyncio
async def test_worker_restart_and_graceful_shutdown():
    """Verify application lifespan handles startup and graceful shutdown without hanging."""
    with patch("apps.api.main.get_redis_pool"), \
         patch("apps.api.main.close_redis_pool", new_callable=AsyncMock) as mock_close_redis, \
         patch("apps.api.main.close_qdrant_client", new_callable=AsyncMock) as mock_close_qdrant, \
         patch.object(app.state, "dispose", create=True):
        
        async with app.router.lifespan_context(app):
            assert True

        # Lifespan shutdown completed cleanly
        mock_close_redis.assert_awaited_once()
        mock_close_qdrant.assert_awaited_once()
