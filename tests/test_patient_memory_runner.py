"""
Verification script for Patient Episodic Memory Service.
"""

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from core.ai.conversation.patient_memory import PatientMemoryService


async def run_verification():
    print("Running Patient Memory Service Verification...")
    svc = PatientMemoryService(collection_name="test_patient_memories")

    # Test 1: Indexing a clinical exchange
    mock_client = AsyncMock()
    mock_client.upsert = AsyncMock()
    with patch("core.ai.conversation.patient_memory.get_qdrant_client", return_value=mock_client), \
         patch("core.ai.conversation.patient_memory.ensure_collection", new_callable=AsyncMock) as mock_ensure, \
         patch("core.ai.conversation.patient_memory.embed_single", new_callable=AsyncMock, return_value=[0.1] * 768):

        ok = await svc.index_exchange(
            user_id="user-test-1",
            patient_id="pat-test-1",
            session_id="sess-test-1",
            user_msg="I have had persistent dizziness and nausea since yesterday morning",
            assistant_msg="Please rest, stay hydrated, and consult a physician to check inner ear or blood pressure.",
        )
        assert ok is True, "Index exchange failed"
        assert mock_client.upsert.called, "Qdrant upsert was not invoked"
        print("  ✅ 1. Indexing clinical consultation exchange: SUCCESS")

    # Test 2: Trivial messages and fast-path actions are ignored
    with patch("core.ai.conversation.patient_memory.get_qdrant_client", return_value=mock_client):
        assert await svc.index_exchange("user-1", "pat-1", "sess-1", "hi", "Hello!") is False
        assert await svc.index_exchange("user-1", "pat-1", "sess-1", "thank you", "You're welcome") is False
        assert await svc.index_exchange("user-1", "pat-1", "sess-1", '{"__action": "confirm"}', "Confirmed") is False
        print("  ✅ 2. Trivial message & JSON payload filtering: SUCCESS")

    # Test 3: Semantic Recall with user_id hard filtering
    mock_point = MagicMock()
    mock_point.score = 0.85
    mock_point.payload = {
        "created_at": "2026-08-15T10:00:00Z",
        "user_msg": "I am severely allergic to penicillin and developed hives",
        "assistant_msg": "Noted penicillin allergy. Avoid all beta-lactam class antibiotics.",
    }
    mock_res = MagicMock()
    mock_res.points = [mock_point]
    mock_client.query_points = AsyncMock(return_value=mock_res)

    with patch("core.ai.conversation.patient_memory.get_qdrant_client", return_value=mock_client), \
         patch("core.ai.conversation.patient_memory.ensure_collection", new_callable=AsyncMock), \
         patch("core.ai.conversation.patient_memory.embed_single", new_callable=AsyncMock, return_value=[0.1] * 768):

        memories = await svc.recall_memories(
            user_id="user-test-1",
            query="Can I take amoxicillin for my bacterial infection?",
            top_k=2,
            score_threshold=0.6,
        )

        assert len(memories) == 1
        assert "penicillin" in memories[0]
        assert "beta-lactam" in memories[0]

        # Verify Qdrant filter contains user_id condition
        call_kwargs = mock_client.query_points.call_args.kwargs
        q_filter = call_kwargs["query_filter"]
        assert q_filter.must[0].key == "user_id"
        assert q_filter.must[0].match.value == "user-test-1"
        print("  ✅ 3. Semantic memory recall & tenant isolation: SUCCESS")

    # Test 4: Error resilience (Qdrant down fallback)
    with patch("core.ai.conversation.patient_memory.get_qdrant_client", side_effect=RuntimeError("Qdrant offline")), \
         patch("core.ai.conversation.patient_memory.embed_single", new_callable=AsyncMock, return_value=[0.1] * 768):

        memories = await svc.recall_memories(user_id="user-1", query="Do I have asthma?")
        assert memories == []
        print("  ✅ 4. Graceful resilience when vector database is unavailable: SUCCESS")

    print("\n🎉 ALL 4 PATIENT MEMORY SYSTEM TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(run_verification())
