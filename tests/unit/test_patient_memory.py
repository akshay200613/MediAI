"""
Unit tests for Patient Episodic Memory Service (Tier 2 Semantic Memory).
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from core.ai.conversation.patient_memory import PatientMemoryService


@pytest.fixture
def memory_service():
    return PatientMemoryService(collection_name="test_patient_memories")


@pytest.mark.asyncio
async def test_index_exchange_success(memory_service):
    mock_client = AsyncMock()
    mock_client.upsert = AsyncMock()

    with patch("core.ai.conversation.patient_memory.get_qdrant_client", return_value=mock_client), \
         patch("core.ai.conversation.patient_memory.ensure_collection", new_callable=AsyncMock) as mock_ensure, \
         patch("core.ai.conversation.patient_memory.embed_single", new_callable=AsyncMock) as mock_embed:
        
        mock_embed.return_value = [0.1] * 768

        success = await memory_service.index_exchange(
            user_id="user-123",
            patient_id="pat-456",
            session_id="sess-789",
            user_msg="I have been having persistent chest tightness after running",
            assistant_msg="Please consult a cardiologist immediately to evaluate cardiovascular health.",
        )

        assert success is True
        mock_ensure.assert_awaited_once()
        mock_embed.assert_awaited_once()
        mock_client.upsert.assert_awaited_once()

        call_args = mock_client.upsert.call_args
        assert call_args.kwargs["collection_name"] == "test_patient_memories"
        points = call_args.kwargs["points"]
        assert len(points) == 1
        assert points[0].payload["user_id"] == "user-123"
        assert points[0].payload["patient_id"] == "pat-456"
        assert points[0].payload["type"] == "consultation_exchange"


@pytest.mark.asyncio
async def test_index_exchange_ignores_trivial_messages(memory_service):
    mock_client = AsyncMock()

    with patch("core.ai.conversation.patient_memory.get_qdrant_client", return_value=mock_client), \
         patch("core.ai.conversation.patient_memory.embed_single", new_callable=AsyncMock) as mock_embed:
        
        # Trivial greetings
        assert await memory_service.index_exchange("u1", "p1", "s1", "hi", "Hello!") is False
        assert await memory_service.index_exchange("u1", "p1", "s1", "thank you", "You're welcome") is False
        # Action JSON payload
        assert await memory_service.index_exchange("u1", "p1", "s1", '{"__action": "confirm"}', "Confirmed") is False
        
        mock_embed.assert_not_awaited()
        mock_client.upsert.assert_not_called()


@pytest.mark.asyncio
async def test_recall_memories_filters_by_user_id(memory_service):
    mock_client = AsyncMock()
    
    mock_point = MagicMock()
    mock_point.score = 0.85
    mock_point.payload = {
        "created_at": "2026-08-15T10:00:00Z",
        "user_msg": "I am allergic to penicillin and developed a rash",
        "assistant_msg": "Recorded penicillin allergy. Do not take amoxicillin or related beta-lactams.",
    }
    
    mock_search_res = MagicMock()
    mock_search_res.points = [mock_point]
    mock_client.query_points = AsyncMock(return_value=mock_search_res)

    with patch("core.ai.conversation.patient_memory.get_qdrant_client", return_value=mock_client), \
         patch("core.ai.conversation.patient_memory.ensure_collection", new_callable=AsyncMock), \
         patch("core.ai.conversation.patient_memory.embed_single", new_callable=AsyncMock) as mock_embed:
        
        mock_embed.return_value = [0.1] * 768

        memories = await memory_service.recall_memories(
            user_id="user-123",
            query="Can I take amoxicillin for my tooth pain?",
            top_k=2,
            score_threshold=0.6,
        )

        assert len(memories) == 1
        assert "penicillin" in memories[0]
        assert "amoxicillin" in memories[0]

        # Verify Qdrant filter contains user_id condition
        call_kwargs = mock_client.query_points.call_args.kwargs
        q_filter = call_kwargs["query_filter"]
        assert q_filter.must[0].key == "user_id"
        assert q_filter.must[0].match.value == "user-123"


@pytest.mark.asyncio
async def test_recall_memories_graceful_fallback_on_error(memory_service):
    with patch("core.ai.conversation.patient_memory.get_qdrant_client", side_effect=RuntimeError("Qdrant offline")), \
         patch("core.ai.conversation.patient_memory.embed_single", new_callable=AsyncMock, return_value=[0.1] * 768):

        memories = await memory_service.recall_memories(
            user_id="user-123",
            query="Do I have asthma?",
        )
        assert memories == []
