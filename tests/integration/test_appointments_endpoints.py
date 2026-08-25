"""
Integration tests for domains/medai/api/v1/appointments.py
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from core.schemas.base import PaginatedResponse
from domains.medai.schemas.appointment import AppointmentOut

_NOW = datetime.now(timezone.utc)


def _appt_out(
    appt_id: uuid.UUID | None = None,
    status: str = "scheduled",
    patient_id: uuid.UUID | None = None,
    doctor_id: uuid.UUID | None = None,
) -> AppointmentOut:
    return AppointmentOut(
        id=appt_id or uuid.uuid4(),
        patient_id=patient_id or uuid.uuid4(),
        doctor_id=doctor_id or uuid.uuid4(),
        appointment_type="consultation",
        status=status,
        scheduled_at=datetime.now(timezone.utc),
        duration_minutes=30,
        reason=None,
        notes=None,
        ai_triage_summary=None,
        is_deleted=False,
        created_at=_NOW,
        updated_at=_NOW,
    )


BASE = "/api/v1/medai/appointments"


# ── GET /appointments ─────────────────────────────────────────────────────────

class TestListAppointments:
    async def test_list_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.get(BASE)
        assert resp.status_code in (401, 403)

    async def test_admin_can_list_all_appointments(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        page = PaginatedResponse(
            data=[_appt_out()],
            total=1, page=1, page_size=20, total_pages=1,
        )
        with patch(
            "domains.medai.services.appointment_service.AppointmentService.list_appointments",
            new=AsyncMock(return_value=page),
        ):
            resp = await async_client.get(BASE, headers=admin_headers)
        assert resp.status_code == 200

    async def test_patient_sees_own_appointments(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        """Patient role triggers patient-record lookup before listing."""
        patient_record = MagicMock()
        patient_record.id = uuid.uuid4()

        with patch(
            "domains.medai.services.patient_service.PatientService.get_patient_by_user_id",
            new=AsyncMock(return_value=patient_record),
        ):
            with patch(
                "domains.medai.services.appointment_service.AppointmentService.get_by_patient",
                new=AsyncMock(return_value=[_appt_out()]),
            ):
                resp = await async_client.get(BASE, headers=patient_headers)
        assert resp.status_code == 200


# ── GET /appointments/{id} ────────────────────────────────────────────────────

class TestGetAppointment:
    async def test_get_existing_appointment(
        self, async_client: AsyncClient, doctor_headers: dict
    ):
        appt = _appt_out()
        with patch(
            "domains.medai.services.appointment_service.AppointmentService.get_appointment",
            new=AsyncMock(return_value=appt),
        ):
            resp = await async_client.get(f"{BASE}/{appt.id}", headers=doctor_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "scheduled"

    async def test_get_missing_appointment_returns_404(
        self, async_client: AsyncClient, doctor_headers: dict
    ):
        with patch(
            "domains.medai.services.appointment_service.AppointmentService.get_appointment",
            new=AsyncMock(return_value=None),
        ):
            resp = await async_client.get(f"{BASE}/{uuid.uuid4()}", headers=doctor_headers)
        assert resp.status_code == 404


# ── POST /appointments/book ───────────────────────────────────────────────────

class TestBookAppointment:
    def _payload(self, patient_id: uuid.UUID, doctor_id: uuid.UUID) -> dict:
        return {
            "patient_id": str(patient_id),
            "doctor_id": str(doctor_id),
            "scheduled_at": datetime.now(timezone.utc).isoformat(),
            "appointment_type": "consultation",
            "duration_minutes": 30,
        }

    async def test_book_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.post(
            f"{BASE}/book",
            json=self._payload(uuid.uuid4(), uuid.uuid4()),
        )
        assert resp.status_code in (401, 403)

    async def test_book_appointment_success(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        pid = uuid.uuid4()
        did = uuid.uuid4()
        appt = _appt_out(patient_id=pid, doctor_id=did)

        # Double-booking check returns nothing
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "domains.medai.services.appointment_service.AppointmentService.create_appointment",
            new=AsyncMock(return_value=appt),
        ):
            with patch(
                "domains.medai.websockets.manager.manager.notify_appointment_event",
                new=AsyncMock(),
            ):
                resp = await async_client.post(
                    f"{BASE}/book",
                    json=self._payload(pid, did),
                    headers=patient_headers,
                )
        assert resp.status_code == 201

    async def test_double_booking_returns_409(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        pid = uuid.uuid4()
        did = uuid.uuid4()

        # Simulate existing appointment at same slot
        existing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute = AsyncMock(return_value=mock_result)

        resp = await async_client.post(
            f"{BASE}/book",
            json=self._payload(pid, did),
            headers=patient_headers,
        )
        assert resp.status_code == 409


# ── POST /appointments/{id}/cancel ────────────────────────────────────────────

class TestCancelAppointment:
    async def test_cancel_scheduled_appointment(
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
                        f"{BASE}/{appt.id}/cancel",
                        headers=doctor_headers,
                    )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "cancelled"

    async def test_cancel_already_cancelled_returns_409(
        self, async_client: AsyncClient, doctor_headers: dict
    ):
        appt = _appt_out(status="cancelled")

        with patch(
            "domains.medai.services.appointment_service.AppointmentService.get_appointment",
            new=AsyncMock(return_value=appt),
        ):
            resp = await async_client.post(
                f"{BASE}/{appt.id}/cancel",
                headers=doctor_headers,
            )
        assert resp.status_code == 409

    async def test_cancel_missing_appointment_returns_404(
        self, async_client: AsyncClient, doctor_headers: dict
    ):
        with patch(
            "domains.medai.services.appointment_service.AppointmentService.get_appointment",
            new=AsyncMock(return_value=None),
        ):
            resp = await async_client.post(
                f"{BASE}/{uuid.uuid4()}/cancel",
                headers=doctor_headers,
            )
        assert resp.status_code == 404
