"""
Integration tests – Authorization Matrix

Verifies that RBAC is enforced correctly across all sensitive endpoints.
Tests that:
  - Patients cannot access admin-only endpoints
  - Doctors cannot manage the knowledge base
  - Admins have broad access
  - Unauthenticated users are always rejected
"""

import uuid
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from domains.medai.schemas.appointment import AppointmentOut

_NOW = datetime.now(timezone.utc)


def _appt_out(
    appt_id: uuid.UUID | None = None,
    status: str = "scheduled",
) -> AppointmentOut:
    return AppointmentOut(
        id=appt_id or uuid.uuid4(),
        patient_id=uuid.uuid4(),
        doctor_id=uuid.uuid4(),
        appointment_type="consultation",
        status=status,
        scheduled_at=_NOW,
        duration_minutes=30,
        reason=None,
        notes=None,
        ai_triage_summary=None,
        is_deleted=False,
        created_at=_NOW,
        updated_at=_NOW,
    )


# ─── RAG ingest – MANAGE_KNOWLEDGE_BASE ──────────────────────────────────────

class TestRagIngestAuthorization:
    _rag_url = "/api/v1/medai/rag/ingest"

    async def test_patient_cannot_ingest(
        self, async_client: AsyncClient, patient_headers: dict
    ):
        resp = await async_client.post(
            self._rag_url,
            headers=patient_headers,
            files={"file": ("doc.txt", BytesIO(b"some text"), "text/plain")},
            data={"title": "Test Doc"},
        )
        assert resp.status_code == 403

    async def test_doctor_cannot_ingest(
        self, async_client: AsyncClient, doctor_headers: dict
    ):
        resp = await async_client.post(
            self._rag_url,
            headers=doctor_headers,
            files={"file": ("doc.txt", BytesIO(b"some text"), "text/plain")},
            data={"title": "Test Doc"},
        )
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_ingest(self, async_client: AsyncClient):
        resp = await async_client.post(
            self._rag_url,
            files={"file": ("doc.txt", BytesIO(b"text"), "text/plain")},
            data={"title": "Test"},
        )
        assert resp.status_code in (401, 403)

    async def test_admin_can_ingest(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        with patch(
            "domains.medai.api.v1.rag.RAGPipeline"
        ) as MockRAG:
            mock_pipeline = MagicMock()
            mock_pipeline.ingest = AsyncMock(return_value=5)
            MockRAG.return_value = mock_pipeline

            resp = await async_client.post(
                self._rag_url,
                headers=admin_headers,
                files={"file": ("doc.txt", BytesIO(b"medical content here"), "text/plain")},
                data={"title": "Clinical Guidelines", "category": "general"},
            )

        assert resp.status_code == 201


# ─── AI Chat – USE_AI_CHAT ────────────────────────────────────────────────────

class TestChatAuthorization:
    _chat_url = "/api/v1/medai/chat"
    # build_medai_graph is an inline import — must patch at the builder module
    _GRAPH_PATCH = "core.ai.graph.builder.build_medai_graph"
    _SM_PATCH = "domains.medai.api.v1.chat.SessionManager"

    def _payload(self) -> dict:
        return {"content": "hello", "session_id": str(uuid.uuid4())}

    def _mock_sm(self):
        mgr = MagicMock()
        mgr.get_last_n_messages = AsyncMock(return_value=[])
        mgr.get_recent_history_cross_session = AsyncMock(return_value=[])
        mgr.add_exchange = AsyncMock()
        return mgr

    async def test_unauthenticated_cannot_chat(self, async_client: AsyncClient):
        resp = await async_client.post(self._chat_url, json=self._payload())
        assert resp.status_code in (401, 403)

    async def test_patient_can_chat(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        """greeting → fast path, no graph needed"""
        with patch(self._SM_PATCH, return_value=self._mock_sm()):
            resp = await async_client.post(
                self._chat_url, json=self._payload(), headers=patient_headers
            )
        assert resp.status_code == 200

    async def test_doctor_can_chat(
        self, async_client: AsyncClient, doctor_headers: dict, mock_session: AsyncMock
    ):
        with patch(self._SM_PATCH, return_value=self._mock_sm()):
            resp = await async_client.post(
                self._chat_url, json=self._payload(), headers=doctor_headers
            )
        assert resp.status_code == 200

    async def test_admin_can_chat(
        self, async_client: AsyncClient, admin_headers: dict, mock_session: AsyncMock
    ):
        with patch(self._SM_PATCH, return_value=self._mock_sm()):
            resp = await async_client.post(
                self._chat_url, json=self._payload(), headers=admin_headers
            )
        assert resp.status_code == 200



# ─── Appointment UPDATE – UPDATE_APPOINTMENT ──────────────────────────────────

class TestAppointmentUpdateAuthorization:
    _base = "/api/v1/medai/appointments"

    async def test_unauthenticated_cannot_patch(self, async_client: AsyncClient):
        resp = await async_client.patch(
            f"{self._base}/{uuid.uuid4()}",
            json={"status": "completed"},
        )
        assert resp.status_code in (401, 403)

    async def test_doctor_can_update(
        self, async_client: AsyncClient, doctor_headers: dict
    ):
        appt = _appt_out()
        updated = _appt_out(appt_id=appt.id, status="completed")
        with patch(
            "domains.medai.services.appointment_service.AppointmentService.update_appointment",
            new=AsyncMock(return_value=updated),
        ):
            with patch(
                "domains.medai.websockets.manager.manager.notify_appointment_event",
                new=AsyncMock(),
            ):
                resp = await async_client.patch(
                    f"{self._base}/{appt.id}",
                    json={"status": "completed"},
                    headers=doctor_headers,
                )
        assert resp.status_code == 200

    async def test_admin_can_update(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        appt = _appt_out()
        updated = _appt_out(appt_id=appt.id, status="completed")
        with patch(
            "domains.medai.services.appointment_service.AppointmentService.update_appointment",
            new=AsyncMock(return_value=updated),
        ):
            with patch(
                "domains.medai.websockets.manager.manager.notify_appointment_event",
                new=AsyncMock(),
            ):
                resp = await async_client.patch(
                    f"{self._base}/{appt.id}",
                    json={"status": "completed"},
                    headers=admin_headers,
                )
        assert resp.status_code == 200


# ─── Appointment CANCEL – patient can only cancel own ─────────────────────────

class TestCancelAuthorizationMatrix:
    _base = "/api/v1/medai/appointments"

    async def test_doctor_can_cancel_any(
        self, async_client: AsyncClient, doctor_headers: dict
    ):
        appt = _appt_out()
        cancelled = _appt_out(appt_id=appt.id, status="cancelled")
        with patch(
            "domains.medai.services.appointment_service.AppointmentService.get_appointment",
            new=AsyncMock(return_value=appt),
        ):
            with patch(
                "domains.medai.services.appointment_service.AppointmentService.cancel_appointment",
                new=AsyncMock(return_value=cancelled),
            ):
                with patch(
                    "domains.medai.websockets.manager.manager.notify_appointment_event",
                    new=AsyncMock(),
                ):
                    resp = await async_client.post(
                        f"{self._base}/{appt.id}/cancel",
                        headers=doctor_headers,
                    )
        assert resp.status_code == 200

    async def test_patient_cannot_cancel_other_patients_appointment(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        """Patient trying to cancel a different patient's appointment → 403."""
        appt = _appt_out()  # Random patient_id ≠ our patient
        with patch(
            "domains.medai.services.appointment_service.AppointmentService.get_appointment",
            new=AsyncMock(return_value=appt),
        ):
            with patch(
                "domains.medai.services.patient_service.PatientService.get_patient_by_user_id",
                new=AsyncMock(return_value=MagicMock(id=uuid.uuid4())),  # different ID
            ):
                resp = await async_client.post(
                    f"{self._base}/{appt.id}/cancel",
                    headers=patient_headers,
                )
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_cancel(self, async_client: AsyncClient):
        resp = await async_client.post(
            f"{self._base}/{uuid.uuid4()}/cancel",
        )
        assert resp.status_code in (401, 403)

    async def test_admin_can_cancel(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        appt = _appt_out()
        cancelled = _appt_out(appt_id=appt.id, status="cancelled")
        with patch(
            "domains.medai.services.appointment_service.AppointmentService.get_appointment",
            new=AsyncMock(return_value=appt),
        ):
            with patch(
                "domains.medai.services.appointment_service.AppointmentService.cancel_appointment",
                new=AsyncMock(return_value=cancelled),
            ):
                with patch(
                    "domains.medai.websockets.manager.manager.notify_appointment_event",
                    new=AsyncMock(),
                ):
                    resp = await async_client.post(
                        f"{self._base}/{appt.id}/cancel",
                        headers=admin_headers,
                    )
        assert resp.status_code == 200


# ─── Admin stats – MANAGE_USERS ──────────────────────────────────────────────

class TestAdminStatsAuthorization:
    _url = "/api/v1/medai/admin/stats"

    async def test_patient_cannot_view_admin_stats(
        self, async_client: AsyncClient, patient_headers: dict
    ):
        resp = await async_client.get(self._url, headers=patient_headers)
        assert resp.status_code == 403

    async def test_doctor_cannot_view_admin_stats(
        self, async_client: AsyncClient, doctor_headers: dict
    ):
        resp = await async_client.get(self._url, headers=doctor_headers)
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_view_admin_stats(
        self, async_client: AsyncClient
    ):
        resp = await async_client.get(self._url)
        assert resp.status_code in (401, 403)


# ─── RAG query – USE_AI_CHAT ──────────────────────────────────────────────────

class TestRagQueryAuthorization:
    _url = "/api/v1/medai/rag/query"

    async def test_unauthenticated_cannot_query_rag(self, async_client: AsyncClient):
        resp = await async_client.post(self._url, json={"query": "headache causes"})
        assert resp.status_code in (401, 403)

    async def test_patient_can_query_rag(
        self, async_client: AsyncClient, patient_headers: dict
    ):
        with patch("domains.medai.api.v1.rag.RAGPipeline") as MockRAG:
            mock_pipeline = MagicMock()
            rag_result = MagicMock()
            rag_result.answer = "Headache causes include dehydration."
            rag_result.sources = []
            rag_result.retrieved_chunks = 2
            rag_result.query = "headache causes"
            mock_pipeline.query = AsyncMock(return_value=rag_result)
            MockRAG.return_value = mock_pipeline

            resp = await async_client.post(
                self._url,
                json={"query": "headache causes"},
                headers=patient_headers,
            )
        assert resp.status_code == 200

    async def test_doctor_can_query_rag(
        self, async_client: AsyncClient, doctor_headers: dict
    ):
        with patch("domains.medai.api.v1.rag.RAGPipeline") as MockRAG:
            mock_pipeline = MagicMock()
            rag_result = MagicMock()
            rag_result.answer = "Clinical guidelines for hypertension."
            rag_result.sources = []
            rag_result.retrieved_chunks = 3
            rag_result.query = "hypertension"
            mock_pipeline.query = AsyncMock(return_value=rag_result)
            MockRAG.return_value = mock_pipeline

            resp = await async_client.post(
                self._url,
                json={"query": "hypertension"},
                headers=doctor_headers,
            )
        assert resp.status_code == 200
