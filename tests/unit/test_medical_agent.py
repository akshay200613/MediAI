"""
Unit tests for domains/medai/ai/agents/medical_agent.py

Tests MedicalAgent.run() with fully mocked LLM and RAG pipeline.
No real LLM or Qdrant connections required.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from core.ai.agents.base_agent import AgentContext, AgentResponse
from core.ai.llm.client import Message
from domains.medai.ai.agents.medical_agent import MedicalAgent


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_llm_client(response_text: str = "Test LLM response") -> MagicMock:
    """Return a mock LLM client whose generate() returns a simple response."""
    llm = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = response_text
    llm.generate = AsyncMock(return_value=mock_resp)
    return llm


def _make_rag_result(answer: str = "RAG answer", sources: list | None = None) -> MagicMock:
    """Return a mock RAG query result."""
    result = MagicMock()
    result.answer = answer
    result.sources = sources or [{"title": "Medical Guidelines", "score": 0.95}]
    result.retrieved_chunks = 3
    return result


def _make_context(
    user_message: str = "What is hypertension?",
    use_rag: bool = True,
    updated_fields: dict | None = None,
    missing_fields: list | None = None,
    patient_name: str = "Test Patient",
) -> AgentContext:
    return AgentContext(
        session_id="test-session-123",
        user_id="user-456",
        domain="medai",
        messages=[Message(role="user", content=user_message)],
        metadata={
            "use_rag": use_rag,
            "updated_fields": updated_fields or {},
            "missing_fields": missing_fields or [],
            "patient_name": patient_name,
        },
    )


# ─── MedicalAgent.run() tests ────────────────────────────────────────────────

class TestMedicalAgentRun:
    async def test_run_uses_rag_by_default(self):
        """When use_rag=True and no updated_fields, rag.query() is called."""
        llm = _make_llm_client()
        rag_result = _make_rag_result("RAG-grounded medical response")

        with patch("domains.medai.ai.agents.medical_agent.RAGPipeline") as MockRAG:
            mock_rag = MagicMock()
            mock_rag.query = AsyncMock(return_value=rag_result)
            MockRAG.return_value = mock_rag

            agent = MedicalAgent(llm_client=llm)
            context = _make_context(use_rag=True)
            response = await agent.run(context)

        mock_rag.query.assert_called_once()
        assert response.content == "RAG-grounded medical response"
        assert response.agent_name == "medical_agent"

    async def test_run_bypasses_rag_when_flag_false(self):
        """When use_rag=False, llm.generate() is called directly, not rag.query()."""
        llm = _make_llm_client("Direct LLM response")

        with patch("domains.medai.ai.agents.medical_agent.RAGPipeline") as MockRAG:
            mock_rag = MagicMock()
            mock_rag.query = AsyncMock()
            MockRAG.return_value = mock_rag

            agent = MedicalAgent(llm_client=llm)
            context = _make_context(use_rag=False)
            response = await agent.run(context)

        mock_rag.query.assert_not_called()
        llm.generate.assert_called_once()
        assert response.content == "Direct LLM response"

    async def test_run_bypasses_rag_on_profile_update(self):
        """updated_fields in metadata forces direct LLM call regardless of use_rag."""
        llm = _make_llm_client("Profile update confirmation")

        with patch("domains.medai.ai.agents.medical_agent.RAGPipeline") as MockRAG:
            mock_rag = MagicMock()
            mock_rag.query = AsyncMock()
            MockRAG.return_value = mock_rag

            agent = MedicalAgent(llm_client=llm)
            context = _make_context(
                use_rag=True,
                updated_fields={"blood_group": "O+", "gender": "male"},
            )
            response = await agent.run(context)

        # RAG must NOT be called when profile was just updated
        mock_rag.query.assert_not_called()
        llm.generate.assert_called_once()
        assert response.content == "Profile update confirmation"

    async def test_run_returns_agent_response_dataclass(self):
        """run() must return an AgentResponse instance."""
        llm = _make_llm_client("Some response")

        with patch("domains.medai.ai.agents.medical_agent.RAGPipeline") as MockRAG:
            mock_rag = MagicMock()
            mock_rag.query = AsyncMock(return_value=_make_rag_result())
            MockRAG.return_value = mock_rag

            agent = MedicalAgent(llm_client=llm)
            result = await agent.run(_make_context())

        assert isinstance(result, AgentResponse)

    async def test_run_includes_sources_from_rag(self):
        """Sources from the RAG result must be propagated to AgentResponse."""
        llm = _make_llm_client()
        sources = [
            {"title": "Clinical Guide v2", "score": 0.98},
            {"title": "WHO Hypertension Report", "score": 0.91},
        ]
        rag_result = _make_rag_result(sources=sources)

        with patch("domains.medai.ai.agents.medical_agent.RAGPipeline") as MockRAG:
            mock_rag = MagicMock()
            mock_rag.query = AsyncMock(return_value=rag_result)
            MockRAG.return_value = mock_rag

            agent = MedicalAgent(llm_client=llm)
            result = await agent.run(_make_context())

        assert result.sources == sources
        assert len(result.sources) == 2

    async def test_run_empty_message_list_direct_llm(self):
        """Empty messages list → direct LLM path (no user_message to RAG)."""
        llm = _make_llm_client("Default response")

        with patch("domains.medai.ai.agents.medical_agent.RAGPipeline") as MockRAG:
            mock_rag = MagicMock()
            mock_rag.query = AsyncMock()
            MockRAG.return_value = mock_rag

            agent = MedicalAgent(llm_client=llm)
            context = AgentContext(
                session_id="s1",
                user_id="u1",
                domain="medai",
                messages=[],  # empty
                metadata={"use_rag": True, "updated_fields": {}, "missing_fields": []},
            )
            result = await agent.run(context)

        # Empty user_message → rag.query is NOT called even with use_rag=True
        mock_rag.query.assert_not_called()
        assert isinstance(result, AgentResponse)

    async def test_missing_fields_extends_system_prompt(self):
        """missing_fields in metadata causes a profile collection prompt to be injected."""
        llm = _make_llm_client("Please provide your blood group")

        with patch("domains.medai.ai.agents.medical_agent.RAGPipeline") as MockRAG:
            mock_rag = MagicMock()
            MockRAG.return_value = mock_rag

            agent = MedicalAgent(llm_client=llm)
            context = _make_context(
                use_rag=False,
                missing_fields=["Blood Group", "Date of Birth"],
                patient_name="Alice Smith",
            )
            result = await agent.run(context)

        # llm.generate is called; check that the system_prompt was extended
        call_kwargs = llm.generate.call_args[1]
        assert "missing" in call_kwargs.get("system_prompt", "").lower() or \
               "Blood Group" in call_kwargs.get("system_prompt", "") or \
               "patient" in call_kwargs.get("system_prompt", "").lower()

    async def test_updated_fields_confirmation_in_prompt(self):
        """updated_fields causes a confirmation system prompt to be injected."""
        llm = _make_llm_client("Great, I've saved your details!")

        with patch("domains.medai.ai.agents.medical_agent.RAGPipeline") as MockRAG:
            MockRAG.return_value = MagicMock()

            agent = MedicalAgent(llm_client=llm)
            context = _make_context(
                use_rag=False,
                updated_fields={"gender": "female"},
                patient_name="Bob Jones",
            )
            result = await agent.run(context)

        call_kwargs = llm.generate.call_args[1]
        system_prompt = call_kwargs.get("system_prompt", "")
        # Must mention the update confirmation instruction
        assert "updated" in system_prompt.lower() or "gender" in system_prompt

    async def test_agent_name_in_response(self):
        """agent_name field must be 'medical_agent'."""
        llm = _make_llm_client()

        with patch("domains.medai.ai.agents.medical_agent.RAGPipeline") as MockRAG:
            mock_rag = MagicMock()
            mock_rag.query = AsyncMock(return_value=_make_rag_result())
            MockRAG.return_value = mock_rag

            agent = MedicalAgent(llm_client=llm)
            result = await agent.run(_make_context())

        assert result.agent_name == "medical_agent"

    async def test_rag_metadata_captured(self):
        """retrieved_chunks from RAG should be in response metadata."""
        llm = _make_llm_client()
        rag_result = _make_rag_result()
        rag_result.retrieved_chunks = 5

        with patch("domains.medai.ai.agents.medical_agent.RAGPipeline") as MockRAG:
            mock_rag = MagicMock()
            mock_rag.query = AsyncMock(return_value=rag_result)
            MockRAG.return_value = mock_rag

            agent = MedicalAgent(llm_client=llm)
            result = await agent.run(_make_context())

        assert result.metadata.get("retrieved_chunks") == 5


# ─── BaseAgent.invoke() error-wrapping ───────────────────────────────────────

class TestBaseAgentInvoke:
    async def test_invoke_wraps_exception_in_agent_response(self):
        """invoke() catches errors from run() and returns a graceful AgentResponse."""
        llm = _make_llm_client()

        with patch("domains.medai.ai.agents.medical_agent.RAGPipeline") as MockRAG:
            mock_rag = MagicMock()
            mock_rag.query = AsyncMock(side_effect=RuntimeError("Qdrant down"))
            MockRAG.return_value = mock_rag

            agent = MedicalAgent(llm_client=llm)
            # invoke() should NOT raise
            result = await agent.invoke(_make_context())

        assert isinstance(result, AgentResponse)
        assert "error" in result.content.lower()
        assert result.agent_name == "medical_agent"
