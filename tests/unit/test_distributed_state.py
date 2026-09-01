"""
Unit Tests for Distributed State Management & Horizontal Scaling.
Validates Redis-backed rate limiting, password reset state, JWT revocation,
distributed caching, distributed locks, multi-worker WebSocket Pub/Sub,
and resilient failure handling.
"""

import asyncio
import json
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.database.redis_keys import (
    key_ratelimit,
    key_revoked_token,
    key_pending_reset_user,
    key_pending_reset_index,
    key_lock,
    key_cache,
    hash_token,
)
from core.cache.distributed_cache import DistributedCache
from core.cache.distributed_lock import DistributedLock
from core.services.password_reset_service import PasswordResetStateManager
from core.auth.token_blacklist import blacklist_token, is_token_blacklisted, _get_token_remaining_ttl
from core.auth.jwt_handler import create_token_pair
from domains.medai.websockets.manager import ConnectionManager
from core.middleware.security import RateLimitMiddleware


# ── 1. Redis Key Namespacing Tests ───────────────────────────────────────────

def test_redis_key_formatting():
    """Verify keys are strictly namespaced under 'medai:'."""
    assert key_ratelimit("ip", "127.0.0.1", "/api/v1/auth/login") == "medai:ratelimit:ip:127.0.0.1:api_v1_auth_login"
    assert key_lock("scheduler") == "medai:lock:scheduler"
    assert key_cache("doctor", "123") == "medai:cache:doctor:123"
    assert key_pending_reset_user("user-456") == "medai:auth:pending_reset:user-456"
    assert key_pending_reset_index() == "medai:auth:pending_resets_set"

    # Token hashing
    test_tok = "my.jwt.token"
    tok_hash = hash_token(test_tok)
    assert len(tok_hash) == 64
    assert key_revoked_token(test_tok) == f"medai:auth:revoked_token:{tok_hash}"


# ── 2. Distributed Cache Tests ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_distributed_cache_set_get_delete_with_redis():
    """Test distributed cache operations when Redis is available."""
    cache = DistributedCache()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=json.dumps({"name": "Dr. Sarah", "specialty": "Cardiology"}))
    mock_redis.setex = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=1)
    mock_redis.exists = AsyncMock(return_value=1)

    with patch("core.cache.distributed_cache.get_redis", return_value=mock_redis):
        # Set
        ok = await cache.set("doc_1", {"name": "Dr. Sarah", "specialty": "Cardiology"}, ttl_seconds=120, domain="doctors")
        assert ok is True
        mock_redis.setex.assert_awaited_once()

        # Get
        val = await cache.get("doc_1", domain="doctors")
        assert val == {"name": "Dr. Sarah", "specialty": "Cardiology"}

        # Exists
        assert await cache.exists("doc_1", domain="doctors") is True

        # Delete
        assert await cache.delete("doc_1", domain="doctors") is True


@pytest.mark.asyncio
async def test_distributed_cache_fallback_when_redis_fails():
    """Test distributed cache gracefully falls back to local storage on Redis failure."""
    cache = DistributedCache()

    with patch("core.cache.distributed_cache.get_redis", side_effect=ConnectionError("Redis down")):
        # Set should store in local fallback
        await cache.set("user_prefs", {"theme": "dark"}, ttl_seconds=60)
        
        # Get should retrieve from local fallback
        val = await cache.get("user_prefs")
        assert val == {"theme": "dark"}

        # Delete removes from local fallback
        await cache.delete("user_prefs")
        assert await cache.get("user_prefs") is None


# ── 3. Distributed Lock Tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_distributed_lock_acquire_and_release():
    """Test distributed lock acquisition and Lua-based safe release with Redis."""
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.eval = AsyncMock(return_value=1)

    with patch("core.cache.distributed_lock.get_redis", return_value=mock_redis):
        lock = DistributedLock("appointment_sync", ttl_seconds=30)
        async with lock as acquired:
            assert acquired is True
            mock_redis.set.assert_awaited_once()

        mock_redis.eval.assert_awaited_once()


@pytest.mark.asyncio
async def test_distributed_lock_contention_across_workers():
    """Test that when Worker 1 holds the lock, Worker 2 is rejected."""
    mock_redis = AsyncMock()
    # First call succeeds (Worker 1), second call returns None/False (Worker 2 fails to acquire)
    mock_redis.set = AsyncMock(side_effect=[True, None])
    mock_redis.eval = AsyncMock(return_value=1)

    with patch("core.cache.distributed_lock.get_redis", return_value=mock_redis):
        w1_lock = DistributedLock("daily_summary_tick", ttl_seconds=10)
        w2_lock = DistributedLock("daily_summary_tick", ttl_seconds=10)

        w1_acquired = await w1_lock.acquire()
        assert w1_acquired is True

        w2_acquired = await w2_lock.acquire()
        assert w2_acquired is False

        await w1_lock.release()


@pytest.mark.asyncio
async def test_distributed_lock_fallback_when_redis_fails():
    """Test distributed lock falls back to process-level asyncio Lock when Redis is down."""
    with patch("core.cache.distributed_lock.get_redis", side_effect=ConnectionError("Redis offline")):
        async with DistributedLock("resilient_task", ttl_seconds=10) as acquired:
            assert acquired is True


# ── 4. Password Reset Distributed State Tests ────────────────────────────────

@pytest.mark.asyncio
async def test_password_reset_state_redis():
    """Test password reset state manager across multiple simulated workers."""
    mgr = PasswordResetStateManager()
    mock_redis = AsyncMock()
    pipe_mock = AsyncMock()
    pipe_mock.setex = MagicMock()
    pipe_mock.sadd = MagicMock()
    pipe_mock.delete = MagicMock()
    pipe_mock.srem = MagicMock()
    pipe_mock.execute = AsyncMock(return_value=[True, 1])
    mock_redis.pipeline = MagicMock(return_value=pipe_mock)
    mock_redis.exists = AsyncMock(return_value=1)
    mock_redis.smembers = AsyncMock(return_value={"user-101", "user-102"})

    with patch("core.services.password_reset_service.get_redis", return_value=mock_redis):
        # Mark pending
        await mgr.mark_pending("user-101", "doctor@example.com", "Dr. John", "doctor")
        pipe_mock.setex.assert_called_once()
        pipe_mock.sadd.assert_called_once()

        # Check pending
        assert await mgr.is_pending("user-101") is True

        # List pending
        pending = await mgr.list_pending_user_ids()
        assert "user-101" in pending

        # Clear pending
        await mgr.clear_pending("user-101")
        pipe_mock.delete.assert_called()


@pytest.mark.asyncio
async def test_password_reset_state_fallback_on_redis_failure():
    """Test password reset state manager uses local fallback when Redis is unreachable."""
    mgr = PasswordResetStateManager()

    with patch("core.services.password_reset_service.get_redis", side_effect=ConnectionError("Redis failure")):
        await mgr.mark_pending("user-999", "patient@example.com", "Patient Jane", "patient")
        assert await mgr.is_pending("user-999") is True
        assert "user-999" in await mgr.list_pending_user_ids()

        await mgr.clear_pending("user-999")
        assert await mgr.is_pending("user-999") is False


# ── 5. JWT Revocation Tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_jwt_revocation_with_redis():
    """Test JWT token revocation with Redis and exp claim parsing."""
    access_tok, _ = create_token_pair("user-1", "user@test.com", "user")
    
    # Calculate TTL from token
    ttl = _get_token_remaining_ttl(access_tok)
    assert ttl > 0

    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value="revoked")

    with patch("core.auth.token_blacklist.get_redis", return_value=mock_redis):
        await blacklist_token(access_tok)
        mock_redis.setex.assert_awaited_once()

        assert await is_token_blacklisted(access_tok) is True


@pytest.mark.asyncio
async def test_jwt_revocation_fallback():
    """Test JWT revocation works with local fallback on Redis downtime."""
    test_token = "some.raw.token.value"
    with patch("core.auth.token_blacklist.get_redis", side_effect=ConnectionError("Redis unavailable")):
        assert await is_token_blacklisted(test_token) is False
        await blacklist_token(test_token, expires_in_seconds=100)
        assert await is_token_blacklisted(test_token) is True


# ── 6. Rate Limiting Middleware Sliding Window Tests ────────────────────────

@pytest.mark.asyncio
async def test_rate_limit_middleware_redis_sliding_window():
    """Test RateLimitMiddleware uses Redis sliding window and returns 429 when threshold exceeded."""
    app_mock = MagicMock()
    middleware = RateLimitMiddleware(app_mock)

    mock_redis = AsyncMock()
    pipe_mock = AsyncMock()
    pipe_mock.zremrangebyscore = MagicMock()
    pipe_mock.zadd = MagicMock()
    pipe_mock.zcard = MagicMock()
    pipe_mock.expire = MagicMock()
    # Simulated count: 12 requests (threshold for /api/v1/auth/login is 10)
    pipe_mock.execute = AsyncMock(return_value=[0, 1, 12, True])
    mock_redis.pipeline = MagicMock(return_value=pipe_mock)

    request_mock = MagicMock()
    request_mock.url.path = "/api/v1/auth/login"
    request_mock.client.host = "192.168.1.50"
    call_next_mock = AsyncMock()

    with patch("core.middleware.security.get_redis", return_value=mock_redis):
        response = await middleware.dispatch(request_mock, call_next_mock)
        assert response.status_code == 429
        assert response.headers.get("Retry-After") == "60"
        call_next_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_rate_limit_middleware_fallback_on_redis_failure():
    """Test RateLimitMiddleware falls back to local tracking without crashing when Redis fails."""
    app_mock = MagicMock()
    middleware = RateLimitMiddleware(app_mock)

    request_mock = MagicMock()
    request_mock.url.path = "/api/v1/auth/register"
    request_mock.client.host = "10.0.0.1"
    
    response_ok = MagicMock()
    response_ok.headers = {}
    call_next_mock = AsyncMock(return_value=response_ok)

    with patch("core.middleware.security.get_redis", side_effect=ConnectionError("Redis down")):
        # First 5 calls pass
        for _ in range(5):
            res = await middleware.dispatch(request_mock, call_next_mock)
            assert res == response_ok

        # 6th call exceeds limit (5 per 60s)
        res_limited = await middleware.dispatch(request_mock, call_next_mock)
        assert res_limited.status_code == 429


# ── 7. Multi-Worker WebSocket Pub/Sub Broadcast Tests ────────────────────────

@pytest.mark.asyncio
async def test_websocket_pubsub_broadcast_distribution():
    """Test ConnectionManager publishes to Redis channel for multi-worker distribution."""
    mgr = ConnectionManager()
    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock(return_value=1)

    with patch("domains.medai.websockets.manager.get_redis", return_value=mock_redis):
        await mgr.notify_appointment_event(
            event_type="appointment_created",
            appointment_data={"id": "appt-123", "doctor": "Dr. Sarah"},
            patient_id="pat-001",
            doctor_id="doc-002",
        )

        mock_redis.publish.assert_awaited_once()
        args = mock_redis.publish.call_args[0]
        channel, message_json = args[0], args[1]
        assert channel == "medai:ws:broadcast"
        data = json.loads(message_json)
        assert data["payload"]["event"] == "appointment_created"
        assert "doc-002" in data["doctor_ids"]
        assert "pat-001" in data["patient_ids"]
