"""
Unit & Regression Tests for Security, Authorization, and Multi-Tenant Isolation.

Covers:
1. Patient A vs Patient B isolation (API endpoints).
2. Malicious LLM-generated patient_id values in MCP tools.
3. Unauthorized appointment access (get/update/cancel).
4. Unauthorized tool execution (patient directory search restriction).
5. Token revocation & logout blacklist.
6. RAG multi-tenant isolation.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from core.auth.dependencies import CurrentUser
from core.ai.graph.tools.context import set_tool_security_context, reset_tool_security_context
from core.auth.token_blacklist import blacklist_token, is_token_blacklisted
from core.ai.rag.pipeline import RAGPipeline
from domains.medai.api.v1.appointments import get_appointment, update_appointment, cancel_appointment
from domains.medai.api.v1.patients import get_patient, update_patient, list_patients
from domains.medai.schemas.appointment import AppointmentUpdate
from domains.medai.schemas.patient import PatientUpdate
from core.ai.graph.tools.appointment_tools import (
    list_appointments as tool_list_appointments,
    book_appointment as tool_book_appointment,
    cancel_appointment as tool_cancel_appointment,
)
from core.ai.graph.tools.patient_tools import (
    get_patient_profile as tool_get_patient_profile,
    get_patient_history as tool_get_patient_history,
    search_patients as tool_search_patients,
)


@pytest.fixture
def patient_a_user():
    return CurrentUser(user_id=str(uuid.uuid4()), email="patientA@example.com", role="patient")


@pytest.fixture
def patient_b_user():
    return CurrentUser(user_id=str(uuid.uuid4()), email="patientB@example.com", role="patient")


@pytest.fixture
def doctor_user():
    return CurrentUser(user_id=str(uuid.uuid4()), email="doctor@example.com", role="doctor")


@pytest.fixture
def admin_user():
    return CurrentUser(user_id=str(uuid.uuid4()), email="admin@example.com", role="admin")


# ==============================================================================
# 1. Cross-User API Authorization & BOLA Isolation
# ==============================================================================

class TestCrossUserAPIIsolation:
    @pytest.mark.asyncio
    async def test_patient_cannot_view_other_patient_appointment(self, patient_a_user, patient_b_user):
        """Patient A must be blocked with 403 when requesting Patient B's appointment."""
        appt_id = uuid.uuid4()
        mock_appt = MagicMock()
        mock_appt.id = appt_id
        mock_appt.patient_id = patient_b_user.user_id
        mock_appt.doctor_id = str(uuid.uuid4())

        mock_session = AsyncMock()
        with patch("domains.medai.api.v1.appointments.AppointmentService") as mock_svc_cls:
            mock_svc = mock_svc_cls.return_value
            mock_svc.get_appointment = AsyncMock(return_value=mock_appt)

            with pytest.raises(HTTPException) as exc_info:
                await get_appointment(appt_id=appt_id, session=mock_session, current_user=patient_a_user)

            assert exc_info.value.status_code == 403
            assert "Access denied" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_patient_cannot_update_other_patient_appointment(self, patient_a_user, patient_b_user):
        """Patient A must be blocked with 403 when updating Patient B's appointment."""
        appt_id = uuid.uuid4()
        mock_appt = MagicMock()
        mock_appt.id = appt_id
        mock_appt.patient_id = patient_b_user.user_id
        mock_appt.doctor_id = str(uuid.uuid4())

        mock_session = AsyncMock()
        with patch("domains.medai.api.v1.appointments.AppointmentService") as mock_svc_cls:
            mock_svc = mock_svc_cls.return_value
            mock_svc.get_appointment = AsyncMock(return_value=mock_appt)

            with pytest.raises(HTTPException) as exc_info:
                await update_appointment(
                    appt_id=appt_id,
                    data=AppointmentUpdate(reason="Tampered"),
                    session=mock_session,
                    current_user=patient_a_user,
                )

            assert exc_info.value.status_code == 403
            assert "Access denied" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_patient_cannot_view_other_patient_profile(self, patient_a_user, patient_b_user):
        """Patient A must be blocked with 403 when viewing Patient B's profile."""
        mock_session = AsyncMock()
        with patch("domains.medai.api.v1.patients.PatientService") as mock_svc_cls:
            mock_svc = mock_svc_cls.return_value
            mock_svc.get_patient_by_user_id = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await get_patient(
                    patient_id=uuid.UUID(patient_b_user.user_id),
                    session=mock_session,
                    current_user=patient_a_user,
                )

            assert exc_info.value.status_code == 403
            assert "Access denied" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_patient_cannot_list_all_patients(self, patient_a_user):
        """Patients must be forbidden from dumping all hospital patients."""
        mock_session = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await list_patients(page=1, page_size=20, search=None, session=mock_session, current_user=patient_a_user)

        assert exc_info.value.status_code == 403
        assert "Patients are not permitted" in exc_info.value.detail


# ==============================================================================
# 2. Malicious LLM-Generated Values & AI Tool Authorization
# ==============================================================================

class TestAIToolSecurityIsolation:
    @pytest.mark.asyncio
    async def test_tool_list_appointments_rejects_foreign_patient_id(self, patient_a_user, patient_b_user):
        """Tool list_appointments must block LLM from accessing Patient B's appointments."""
        token = set_tool_security_context(
            user_id=patient_a_user.user_id,
            role="patient",
            email=patient_a_user.email,
        )
        try:
            # LLM maliciously or hallucinatorily passed Patient B's ID
            res = await tool_list_appointments(patient_id=patient_b_user.user_id)
            assert res["count"] == 0
            assert "error" in res
            assert "Unauthorized" in res["error"]
        finally:
            reset_tool_security_context(token)

    @pytest.mark.asyncio
    async def test_tool_book_appointment_overrides_malicious_patient_id(self, patient_a_user, patient_b_user):
        """Tool book_appointment overrides malicious patient_id with caller's verified ID."""
        token = set_tool_security_context(
            user_id=patient_a_user.user_id,
            patient_id=patient_a_user.user_id,
            role="patient",
            email=patient_a_user.email,
        )
        try:
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session.commit = AsyncMock()

            with patch("core.ai.graph.tools.appointment_tools.AsyncSessionLocal", return_value=mock_session):
                with patch("domains.medai.services.appointment_service.AppointmentService.create_appointment") as mock_create:
                    mock_appt = MagicMock()
                    mock_appt.model_dump.return_value = {"id": "123", "patient_id": patient_a_user.user_id}
                    mock_create.return_value = mock_appt

                    # LLM attempted to book for Patient B
                    res = await tool_book_appointment(
                        patient_id=patient_b_user.user_id,
                        doctor_id=str(uuid.uuid4()),
                        scheduled_at="2026-10-15T10:00:00",
                    )
                    assert res["success"] is True
                    # Verified that the create call received Patient A's ID
                    created_arg = mock_create.call_args[0][0]
                    assert str(created_arg.patient_id) == str(patient_a_user.user_id)
        finally:
            reset_tool_security_context(token)

    @pytest.mark.asyncio
    async def test_tool_cancel_appointment_blocks_foreign_appointment(self, patient_a_user, patient_b_user):
        """Tool cancel_appointment must block cancelling another patient's appointment."""
        token = set_tool_security_context(
            user_id=patient_a_user.user_id,
            patient_id=patient_a_user.user_id,
            role="patient",
            email=patient_a_user.email,
        )
        try:
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None

            mock_appt = MagicMock()
            mock_appt.id = uuid.uuid4()
            mock_appt.patient_id = patient_b_user.user_id

            with patch("core.ai.graph.tools.appointment_tools.AsyncSessionLocal", return_value=mock_session):
                with patch("domains.medai.services.appointment_service.AppointmentService.get_appointment", return_value=mock_appt):
                    res = await tool_cancel_appointment(appointment_id=str(mock_appt.id))
                    assert res["success"] is False
                    assert "Unauthorized" in res["error"]
        finally:
            reset_tool_security_context(token)

    @pytest.mark.asyncio
    async def test_tool_search_patients_blocked_for_patients(self, patient_a_user):
        """Tool search_patients must reject patient callers."""
        token = set_tool_security_context(
            user_id=patient_a_user.user_id,
            role="patient",
            email=patient_a_user.email,
        )
        try:
            res = await tool_search_patients(query="John")
            assert res["count"] == 0
            assert "Unauthorized" in res["error"]
        finally:
            reset_tool_security_context(token)


# ==============================================================================
# 3. Token Revocation & Logout Security
# ==============================================================================

class TestTokenBlacklistSecurity:
    @pytest.mark.asyncio
    async def test_blacklisted_token_is_identified_as_revoked(self):
        """Revoked tokens must be detected as blacklisted."""
        test_token = f"test-token-{uuid.uuid4()}"
        assert await is_token_blacklisted(test_token) is False

        await blacklist_token(test_token, expires_in_seconds=60)
        assert await is_token_blacklisted(test_token) is True


# ==============================================================================
# 4. RAG Access Control & Multi-Tenant Isolation
# ==============================================================================

class TestRAGTenantAccessControl:
    @pytest.mark.asyncio
    async def test_rag_query_filters_out_private_consultation_notes_for_general_queries(self):
        """General RAG queries must not leak private patient consultation notes."""
        pipeline = RAGPipeline(
            llm_client=MagicMock(),
            collection_name="test_medai_knowledge",
        )

        mock_general_chunk = MagicMock()
        mock_general_chunk.text = "Hospital is open 24/7."
        mock_general_chunk.metadata = {"category": "facilities"}
        mock_general_chunk.score = 0.95

        mock_private_chunk = MagicMock()
        mock_private_chunk.text = "Patient John Doe has acute pneumonia. Prescribed Azithromycin."
        mock_private_chunk.metadata = {"category": "consultation_notes", "patient_id": "patient-b-123"}
        mock_private_chunk.score = 0.98

        pipeline.llm.embed = AsyncMock(return_value=[0.1] * 768)
        pipeline.hybrid_retriever.search = AsyncMock(return_value=[mock_private_chunk, mock_general_chunk])
        pipeline.llm.generate = AsyncMock(return_value=MagicMock(content="Hospital info response"))

        # General query with no patient_id filter
        res = await pipeline.query(user_query="What are the hospital hours?")

        # The private chunk should have been filtered out before prompt generation
        assert len(res.sources) == 1
        assert res.sources[0]["category"] == "facilities"
