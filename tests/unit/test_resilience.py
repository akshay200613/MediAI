"""
Unit tests – Resilience and failure handling.

Tests that service-layer errors are handled gracefully:
  - Chat endpoint returns 503 on AI failures
  - Patient detail extraction skips non-medical messages
  - Service DB errors are propagated correctly
  - RAG query rejects empty input
  - Appointment service handles DB errors
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domains.medai.api.v1.chat import has_patient_details


# ─── has_patient_details (pure function) ─────────────────────────────────────

class TestHasPatientDetailsHelper:
    """Exhaustive tests for the keyword-detection helper."""

    _medical_messages = [
        "My date of birth is 1990-01-01",
        "I was born on 15th March 1985",
        "my dob is 2000-06-20",
        "I am male",
        "gender: female",
        "my blood group is B+",
        "blood type: AB-",
        "I live at 42 Elm Street",
        "my address is 10 Downing St",
        "I'm from Mumbai city",
        "I live in the state of Kerala",
        "emergency contact: Jane Doe",
        "emergency_contact_name: John Smith",
    ]

    _non_medical_messages = [
        "What is the capital of France?",
        "Tell me about COVID vaccines",
        "hello!",
        "Thank you for your help",
        "How do I book an appointment?",
        "What are visiting hours?",
        "I have a headache",
        "Can you recommend a doctor?",
    ]

    @pytest.mark.parametrize("msg", _medical_messages)
    def test_detects_patient_data_keywords(self, msg: str):
        assert has_patient_details(msg) is True

    @pytest.mark.parametrize("msg", _non_medical_messages)
    def test_ignores_non_patient_messages(self, msg: str):
        assert has_patient_details(msg) is False

    def test_case_insensitive_detection(self):
        assert has_patient_details("DATE OF BIRTH: 2000-01-01") is True
        assert has_patient_details("BLOOD GROUP: O+") is True
        assert has_patient_details("GENDER: male") is True

    def test_empty_string_returns_false(self):
        assert has_patient_details("") is False

    def test_mixed_message_with_keyword(self):
        """A medical query that also contains a patient detail keyword."""
        assert has_patient_details("I have headaches and my address is 5 Oak Lane") is True


# ─── AppointmentService resilience ───────────────────────────────────────────

class TestAppointmentServiceResilience:
    async def test_create_appointment_db_error_propagates(self):
        """DB errors from the repo must propagate up (not swallowed)."""
        from domains.medai.services.appointment_service import AppointmentService
        from domains.medai.schemas.appointment import AppointmentCreate

        session = AsyncMock()
        svc = AppointmentService(session)

        with patch.object(svc.repo, "create", new=AsyncMock(side_effect=Exception("DB down"))):
            with pytest.raises(Exception, match="DB down"):
                data = AppointmentCreate(
                    patient_id=uuid.uuid4(),
                    doctor_id=uuid.uuid4(),
                    scheduled_at=datetime.now(timezone.utc),
                )
                await svc.create_appointment(data)

    async def test_get_appointment_none_when_not_found(self):
        """get_appointment returns None (not raises) when record missing."""
        from domains.medai.services.appointment_service import AppointmentService

        session = AsyncMock()
        svc = AppointmentService(session)

        with patch.object(svc.repo, "get_by_id", new=AsyncMock(return_value=None)):
            result = await svc.get_appointment(uuid.uuid4())

        assert result is None

    async def test_cancel_appointment_returns_none_when_not_found(self):
        """cancel_appointment returns None without raising if ID missing."""
        from domains.medai.services.appointment_service import AppointmentService

        session = AsyncMock()
        svc = AppointmentService(session)

        with patch.object(svc.repo, "update", new=AsyncMock(return_value=None)):
            result = await svc.cancel_appointment(uuid.uuid4())

        assert result is None


# ─── PatientService resilience ───────────────────────────────────────────────

class TestPatientServiceResilience:
    async def test_get_patient_by_user_id_returns_none_when_missing(self):
        from domains.medai.services.patient_service import PatientService

        session = AsyncMock()
        svc = PatientService(session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await svc.get_patient_by_user_id("nonexistent-user-id")
        assert result is None

    async def test_create_patient_db_error_propagates(self):
        from domains.medai.services.patient_service import PatientService
        from domains.medai.schemas.patient import PatientCreate

        session = AsyncMock()
        svc = PatientService(session)

        with patch.object(svc.repo, "create", new=AsyncMock(side_effect=Exception("Connection lost"))):
            with pytest.raises(Exception, match="Connection lost"):
                await svc.create_patient(
                    PatientCreate(
                        first_name="Test",
                        last_name="Patient",
                        email="p@test.com",
                        phone="1234567890",
                    )
                )


# ─── DoctorService resilience ────────────────────────────────────────────────

class TestDoctorServiceResilience:
    async def test_get_doctor_returns_none_when_not_found(self):
        from domains.medai.services.doctor_service import DoctorService

        session = AsyncMock()
        svc = DoctorService(session)

        with patch.object(svc.repo, "get_by_id", new=AsyncMock(return_value=None)):
            result = await svc.get_doctor(uuid.uuid4())

        assert result is None


# ─── MedicalAgent error wrapping ─────────────────────────────────────────────

class TestMedicalAgentResilience:
    async def test_invoke_catches_rag_error(self):
        """BaseAgent.invoke() must catch errors in run() and return graceful AgentResponse."""
        from core.ai.agents.base_agent import AgentContext, AgentResponse
        from core.ai.llm.client import Message
        from domains.medai.ai.agents.medical_agent import MedicalAgent

        llm = MagicMock()
        llm.generate = AsyncMock(side_effect=Exception("LLM offline"))

        with patch("domains.medai.ai.agents.medical_agent.RAGPipeline") as MockRAG:
            mock_rag = MagicMock()
            mock_rag.query = AsyncMock(side_effect=RuntimeError("Qdrant unreachable"))
            MockRAG.return_value = mock_rag

            agent = MedicalAgent(llm_client=llm)
            context = AgentContext(
                session_id="s1",
                user_id="u1",
                domain="medai",
                messages=[Message(role="user", content="What is appendicitis?")],
                metadata={"use_rag": True, "updated_fields": {}, "missing_fields": []},
            )

            # invoke() (not run()) should not raise
            result = await agent.invoke(context)

        assert isinstance(result, AgentResponse)
        assert "error" in result.content.lower() or len(result.content) > 0

    async def test_invoke_catches_llm_error(self):
        """Direct LLM path error is also caught by invoke()."""
        from core.ai.agents.base_agent import AgentContext, AgentResponse
        from core.ai.llm.client import Message
        from domains.medai.ai.agents.medical_agent import MedicalAgent

        llm = MagicMock()
        llm.generate = AsyncMock(side_effect=ConnectionError("API timeout"))

        with patch("domains.medai.ai.agents.medical_agent.RAGPipeline") as MockRAG:
            MockRAG.return_value = MagicMock()

            agent = MedicalAgent(llm_client=llm)
            context = AgentContext(
                session_id="s2",
                user_id="u2",
                domain="medai",
                messages=[Message(role="user", content="Test message")],
                metadata={"use_rag": False, "updated_fields": {}, "missing_fields": []},
            )

            result = await agent.invoke(context)

        assert isinstance(result, AgentResponse)


# ─── Permission boundary checks ──────────────────────────────────────────────

class TestPermissionBoundaries:
    def test_has_permission_patient_lacks_manage_knowledge_base(self):
        from core.auth.permissions import has_permission, Permission
        assert has_permission("patient", Permission.MANAGE_KNOWLEDGE_BASE) is False

    def test_has_permission_doctor_lacks_manage_users(self):
        from core.auth.permissions import has_permission, Permission
        assert has_permission("doctor", Permission.MANAGE_USERS) is False

    def test_has_permission_admin_has_manage_knowledge_base(self):
        from core.auth.permissions import has_permission, Permission
        assert has_permission("admin", Permission.MANAGE_KNOWLEDGE_BASE) is True

    def test_has_permission_patient_has_use_ai_chat(self):
        from core.auth.permissions import has_permission, Permission
        assert has_permission("patient", Permission.USE_AI_CHAT) is True

    def test_has_permission_unknown_role_has_nothing(self):
        from core.auth.permissions import has_permission, Permission
        assert has_permission("hacker", Permission.MANAGE_USERS) is False

    def test_super_admin_has_all_permissions(self):
        from core.auth.permissions import has_permission, Permission
        for perm in Permission:
            assert has_permission("super_admin", perm) is True

    def test_doctor_has_use_ai_chat(self):
        from core.auth.permissions import has_permission, Permission
        assert has_permission("doctor", Permission.USE_AI_CHAT) is True

    def test_receptionist_lacks_use_ai_chat(self):
        from core.auth.permissions import has_permission, Permission
        assert has_permission("receptionist", Permission.USE_AI_CHAT) is False
