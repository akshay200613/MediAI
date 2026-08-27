"""
Integration tests for the AI Chat API endpoints.

Tests /api/v1/medai/chat (POST),
      /api/v1/medai/chat/sessions (GET),
      /api/v1/medai/chat/sessions/{id}/messages (GET),
      /api/v1/medai/chat/sessions/{id} (DELETE)

All LangGraph / LLM calls are mocked – no real AI service is required.

NOTE on patch targets:
  - `build_medai_graph` is an inline import inside chat() so must be patched at
    "core.ai.graph.builder.build_medai_graph"
  - `SessionManager` is a top-level import in chat.py so patch at
    "domains.medai.api.v1.chat.SessionManager"
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from langchain_core.messages import AIMessage

CHAT_BASE = "/api/v1/medai/chat"

# Correct patch target for the inline-imported graph builder
_GRAPH_PATCH = "core.ai.graph.builder.build_medai_graph"
_SESSION_MGR_PATCH = "domains.medai.api.v1.chat.SessionManager"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_graph_result(text: str = "Here is some medical advice.") -> dict:
    """Build a minimal state dict that the chat endpoint expects back from the graph."""
    msg = MagicMock(spec=AIMessage)
    msg.content = text
    msg.tool_calls = []
    return {
        "messages": [msg],
        "final_response": text,
        "current_agent": "medical_agent",
    }


def _mock_session_manager() -> MagicMock:
    mgr = MagicMock()
    mgr.get_last_n_messages = AsyncMock(return_value=[])
    mgr.get_recent_history_cross_session = AsyncMock(return_value=[])
    mgr.add_exchange = AsyncMock()
    mgr.clear = AsyncMock()
    return mgr


def _mock_graph(text: str = "Medical response") -> MagicMock:
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value=_make_graph_result(text))
    return mock_graph


# ─── POST /chat ───────────────────────────────────────────────────────────────

class TestPostChat:
    async def test_chat_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.post(
            CHAT_BASE,
            json={"content": "hello", "session_id": str(uuid.uuid4())},
        )
        assert resp.status_code in (401, 403)

    async def test_chat_small_talk_greeting_bypasses_graph(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        """Greeting messages are short-circuited without hitting LangGraph."""
        # Greeting fast-path still needs SessionManager.add_exchange
        with patch(_SESSION_MGR_PATCH, return_value=_mock_session_manager()):
            resp = await async_client.post(
                CHAT_BASE,
                json={"content": "hello", "session_id": str(uuid.uuid4())},
                headers=patient_headers,
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "MedAI" in body["data"]["content"] or "Hello" in body["data"]["content"]

    async def test_chat_small_talk_thanks_bypasses_graph(
        self, async_client: AsyncClient, patient_headers: dict
    ):
        with patch(_SESSION_MGR_PATCH, return_value=_mock_session_manager()):
            resp = await async_client.post(
                CHAT_BASE,
                json={"content": "thank you", "session_id": str(uuid.uuid4())},
                headers=patient_headers,
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "welcome" in body["data"]["content"].lower() or body["success"] is True

    async def test_chat_medical_query_uses_graph(
        self, async_client: AsyncClient, doctor_headers: dict, mock_session: AsyncMock
    ):
        """A real medical question goes through LangGraph (mocked at builder level)."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(_SESSION_MGR_PATCH, return_value=_mock_session_manager()):
            with patch(_GRAPH_PATCH, return_value=_mock_graph("Consult a cardiologist.")):
                resp = await async_client.post(
                    CHAT_BASE,
                    json={
                        "content": "I have chest pain, what should I do?",
                        "session_id": str(uuid.uuid4()),
                        "use_rag": True,
                    },
                    headers=doctor_headers,
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True

    async def test_chat_patient_role_uses_graph(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        """Patient role triggers patient-record lookup + background task."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(_SESSION_MGR_PATCH, return_value=_mock_session_manager()):
            with patch(_GRAPH_PATCH, return_value=_mock_graph("I can help with that.")):
                resp = await async_client.post(
                    CHAT_BASE,
                    json={
                        "content": "What are symptoms of diabetes?",
                        "session_id": str(uuid.uuid4()),
                    },
                    headers=patient_headers,
                )

        assert resp.status_code == 200

    async def test_chat_returns_503_on_ai_service_unavailable(
        self, async_client: AsyncClient, doctor_headers: dict, mock_session: AsyncMock
    ):
        """AIServiceUnavailableError must map to 503."""
        from core.ai.llm.litellm_client import AIServiceUnavailableError

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        bad_graph = MagicMock()
        bad_graph.ainvoke = AsyncMock(side_effect=AIServiceUnavailableError("LLM down"))

        with patch(_SESSION_MGR_PATCH, return_value=_mock_session_manager()):
            with patch(_GRAPH_PATCH, return_value=bad_graph):
                resp = await async_client.post(
                    CHAT_BASE,
                    json={"content": "What is hypertension?", "session_id": str(uuid.uuid4())},
                    headers=doctor_headers,
                )

        assert resp.status_code == 503

    async def test_chat_returns_503_on_generic_graph_exception(
        self, async_client: AsyncClient, doctor_headers: dict, mock_session: AsyncMock
    ):
        """Any unexpected exception in the graph should still return 503."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        bad_graph = MagicMock()
        bad_graph.ainvoke = AsyncMock(side_effect=RuntimeError("unexpected error"))

        with patch(_SESSION_MGR_PATCH, return_value=_mock_session_manager()):
            with patch(_GRAPH_PATCH, return_value=bad_graph):
                resp = await async_client.post(
                    CHAT_BASE,
                    json={"content": "Tell me about insulin.", "session_id": str(uuid.uuid4())},
                    headers=doctor_headers,
                )

        assert resp.status_code == 503

    async def test_chat_response_structure(
        self, async_client: AsyncClient, doctor_headers: dict, mock_session: AsyncMock
    ):
        """Response payload must contain all ChatResponse fields."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(_SESSION_MGR_PATCH, return_value=_mock_session_manager()):
            with patch(_GRAPH_PATCH, return_value=_mock_graph("Insulin regulates blood sugar.")):
                resp = await async_client.post(
                    CHAT_BASE,
                    json={"content": "Explain insulin.", "session_id": str(uuid.uuid4())},
                    headers=doctor_headers,
                )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "content" in data
        assert "session_id" in data
        assert "agent_name" in data
        assert "sources" in data

    async def test_chat_admin_can_also_use_chat(
        self, async_client: AsyncClient, admin_headers: dict, mock_session: AsyncMock
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(_SESSION_MGR_PATCH, return_value=_mock_session_manager()):
            with patch(_GRAPH_PATCH, return_value=_mock_graph("Admin response.")):
                resp = await async_client.post(
                    CHAT_BASE,
                    json={"content": "Summarize patient record.", "session_id": str(uuid.uuid4())},
                    headers=admin_headers,
                )

        assert resp.status_code == 200


# ─── GET /chat/sessions ───────────────────────────────────────────────────────

class TestGetSessions:
    async def test_get_sessions_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.get(f"{CHAT_BASE}/sessions")
        assert resp.status_code in (401, 403)

    async def test_get_sessions_returns_list(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        """Returns a list of sessions (may be empty)."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        resp = await async_client.get(f"{CHAT_BASE}/sessions", headers=patient_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert isinstance(body["data"], list)

    async def test_doctor_can_get_sessions(
        self, async_client: AsyncClient, doctor_headers: dict, mock_session: AsyncMock
    ):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        resp = await async_client.get(f"{CHAT_BASE}/sessions", headers=doctor_headers)
        assert resp.status_code == 200


# ─── GET /chat/sessions/{id}/messages ────────────────────────────────────────

class TestGetSessionMessages:
    async def test_get_messages_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.get(f"{CHAT_BASE}/sessions/{uuid.uuid4()}/messages")
        assert resp.status_code in (401, 403)

    async def test_get_messages_session_not_found_returns_empty(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        """If session not found or belongs to other user, endpoint returns empty data."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        resp = await async_client.get(
            f"{CHAT_BASE}/sessions/{uuid.uuid4()}/messages",
            headers=patient_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False or body["data"] == []


# ─── DELETE /chat/sessions/{id} ──────────────────────────────────────────────

class TestDeleteSession:
    async def test_delete_session_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.delete(f"{CHAT_BASE}/sessions/{uuid.uuid4()}")
        assert resp.status_code in (401, 403)

    async def test_delete_session_returns_204(
        self, async_client: AsyncClient, patient_headers: dict
    ):
        with patch(_SESSION_MGR_PATCH, return_value=_mock_session_manager()):
            resp = await async_client.delete(
                f"{CHAT_BASE}/sessions/{uuid.uuid4()}",
                headers=patient_headers,
            )
        assert resp.status_code == 204


# ─── has_patient_details helper ──────────────────────────────────────────────

class TestHasPatientDetails:
    def test_detects_date_of_birth(self):
        from domains.medai.api.v1.chat import has_patient_details
        assert has_patient_details("My date of birth is 1990-01-01") is True

    def test_detects_blood_group(self):
        from domains.medai.api.v1.chat import has_patient_details
        assert has_patient_details("My blood group is O+") is True

    def test_detects_gender(self):
        from domains.medai.api.v1.chat import has_patient_details
        assert has_patient_details("I am male") is True

    def test_detects_address(self):
        from domains.medai.api.v1.chat import has_patient_details
        assert has_patient_details("My address is 123 Main St") is True

    def test_detects_emergency_contact(self):
        from domains.medai.api.v1.chat import has_patient_details
        assert has_patient_details("My emergency contact is John") is True

    def test_returns_false_for_generic_message(self):
        from domains.medai.api.v1.chat import has_patient_details
        assert has_patient_details("What are symptoms of flu?") is False

    def test_returns_false_for_greeting(self):
        from domains.medai.api.v1.chat import has_patient_details
        assert has_patient_details("Hello, how are you?") is False

    def test_detects_city(self):
        from domains.medai.api.v1.chat import has_patient_details
        assert has_patient_details("I live in the city of Mumbai") is True

    def test_detects_state(self):
        from domains.medai.api.v1.chat import has_patient_details
        assert has_patient_details("My state is California") is True

    def test_case_insensitive(self):
        from domains.medai.api.v1.chat import has_patient_details
        assert has_patient_details("DATE OF BIRTH: 2000-05-10") is True
