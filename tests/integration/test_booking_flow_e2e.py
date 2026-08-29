"""
Integration test – Complete Booking Flow E2E

Exercises the full happy-path booking lifecycle without a real database:
  1. List appointments as patient (initially empty)
  2. Book an appointment
  3. Retrieve the specific appointment
  4. List booked slots for that doctor
  5. Cancel the appointment
  6. Verify status changed to 'cancelled'
  7. Attempt to cancel again → 409 Conflict

All service calls are mocked at the service-layer boundary.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from domains.medai.schemas.appointment import AppointmentOut
from core.schemas.base import PaginatedResponse

BASE = "/api/v1/medai/appointments"
_NOW = datetime.now(timezone.utc)


def _appt_out(
    appt_id: uuid.UUID | None = None,
    status: str = "scheduled",
    patient_id: uuid.UUID | None = None,
    doctor_id: uuid.UUID | None = None,
    scheduled_at: datetime | None = None,
) -> AppointmentOut:
    return AppointmentOut(
        id=appt_id or uuid.uuid4(),
        patient_id=patient_id or uuid.uuid4(),
        doctor_id=doctor_id or uuid.uuid4(),
        appointment_type="consultation",
        status=status,
        scheduled_at=scheduled_at or _NOW,
        duration_minutes=30,
        reason="Regular checkup",
        notes=None,
        ai_triage_summary=None,
        is_deleted=False,
        created_at=_NOW,
        updated_at=_NOW,
    )


class TestCompleteBookingFlow:
    """
    Tests the complete lifecycle: list → book → get → booked-slots → cancel → re-cancel.
    """

    # Shared state across the booking flow steps
    _patient_id = uuid.uuid4()
    _doctor_id = uuid.uuid4()
    _appt_id = uuid.uuid4()
    _slot = datetime.now(timezone.utc)

    def _payload(self) -> dict:
        return {
            "patient_id": str(self._patient_id),
            "doctor_id": str(self._doctor_id),
            "scheduled_at": self._slot.isoformat(),
            "appointment_type": "consultation",
            "duration_minutes": 30,
            "reason": "Regular checkup",
        }

    # ── Step 1: List – empty ──────────────────────────────────────────────────
    async def test_step1_list_appointments_empty_initially(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        empty_page = PaginatedResponse(data=[], total=0, page=1, page_size=20, total_pages=0)
        with patch(
            "domains.medai.services.appointment_service.AppointmentService.list_appointments",
            new=AsyncMock(return_value=empty_page),
        ):
            resp = await async_client.get(BASE, headers=admin_headers)

        assert resp.status_code == 200
        assert resp.json()["data"] == []

    # ── Step 2: Book ─────────────────────────────────────────────────────────
    async def test_step2_book_appointment_returns_201(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        booked = _appt_out(
            appt_id=self._appt_id,
            patient_id=self._patient_id,
            doctor_id=self._doctor_id,
            scheduled_at=self._slot,
        )
        no_conflict = MagicMock()
        no_conflict.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=no_conflict)

        with patch(
            "domains.medai.services.appointment_service.AppointmentService.create_appointment",
            new=AsyncMock(return_value=booked),
        ):
            with patch(
                "domains.medai.websockets.manager.manager.notify_appointment_event",
                new=AsyncMock(),
            ):
                resp = await async_client.post(
                    f"{BASE}/book",
                    json=self._payload(),
                    headers=patient_headers,
                )

        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["status"] == "scheduled"
        assert data["id"] == str(self._appt_id)

    # ── Step 3: Get by ID ─────────────────────────────────────────────────────
    async def test_step3_get_appointment_by_id(
        self, async_client: AsyncClient, doctor_headers: dict
    ):
        booked = _appt_out(
            appt_id=self._appt_id,
            patient_id=self._patient_id,
            doctor_id=self._doctor_id,
        )
        with patch(
            "domains.medai.services.appointment_service.AppointmentService.get_appointment",
            new=AsyncMock(return_value=booked),
        ):
            resp = await async_client.get(
                f"{BASE}/{self._appt_id}", headers=doctor_headers
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == str(self._appt_id)
        assert data["status"] == "scheduled"

    # ── Step 4: Booked slots ──────────────────────────────────────────────────
    async def test_step4_booked_slots_contains_our_slot(
        self, async_client: AsyncClient, doctor_headers: dict, mock_session: AsyncMock
    ):
        mock_scalars = MagicMock()
        mock_scalars.scalars.return_value = [self._slot, self._slot]
        mock_session.execute = AsyncMock(return_value=mock_scalars)


        resp = await async_client.get(
            f"{BASE}/booked-slots",
            params={
                "doctor_id": str(self._doctor_id),
                "date": self._slot.strftime("%Y-%m-%d"),
            },
            headers=doctor_headers,
        )

        assert resp.status_code == 200
        slots = resp.json()["data"]
        assert len(slots) >= 1

    # ── Step 5: Cancel ────────────────────────────────────────────────────────
    async def test_step5_cancel_appointment(
        self, async_client: AsyncClient, doctor_headers: dict
    ):
        scheduled = _appt_out(
            appt_id=self._appt_id,
            patient_id=self._patient_id,
            doctor_id=self._doctor_id,
        )
        cancelled = _appt_out(
            appt_id=self._appt_id,
            patient_id=self._patient_id,
            doctor_id=self._doctor_id,
            status="cancelled",
        )
        with patch(
            "domains.medai.services.appointment_service.AppointmentService.get_appointment",
            new=AsyncMock(return_value=scheduled),
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
                        f"{BASE}/{self._appt_id}/cancel",
                        headers=doctor_headers,
                    )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "cancelled"

    # ── Step 6: Get again – should be cancelled ───────────────────────────────
    async def test_step6_get_after_cancel_shows_cancelled_status(
        self, async_client: AsyncClient, doctor_headers: dict
    ):
        cancelled = _appt_out(
            appt_id=self._appt_id,
            patient_id=self._patient_id,
            doctor_id=self._doctor_id,
            status="cancelled",
        )
        with patch(
            "domains.medai.services.appointment_service.AppointmentService.get_appointment",
            new=AsyncMock(return_value=cancelled),
        ):
            resp = await async_client.get(
                f"{BASE}/{self._appt_id}", headers=doctor_headers
            )

        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "cancelled"

    # ── Step 7: Re-cancel → 409 ───────────────────────────────────────────────
    async def test_step7_re_cancel_already_cancelled_returns_409(
        self, async_client: AsyncClient, doctor_headers: dict
    ):
        already_cancelled = _appt_out(
            appt_id=self._appt_id,
            patient_id=self._patient_id,
            doctor_id=self._doctor_id,
            status="cancelled",
        )
        with patch(
            "domains.medai.services.appointment_service.AppointmentService.get_appointment",
            new=AsyncMock(return_value=already_cancelled),
        ):
            resp = await async_client.post(
                f"{BASE}/{self._appt_id}/cancel",
                headers=doctor_headers,
            )

        assert resp.status_code == 409
        assert "already" in resp.json()["detail"].lower()

    # ── Additional: Get non-existent → 404 ───────────────────────────────────
    async def test_get_nonexistent_appointment_returns_404(
        self, async_client: AsyncClient, doctor_headers: dict
    ):
        with patch(
            "domains.medai.services.appointment_service.AppointmentService.get_appointment",
            new=AsyncMock(return_value=None),
        ):
            resp = await async_client.get(
                f"{BASE}/{uuid.uuid4()}", headers=doctor_headers
            )

        assert resp.status_code == 404

    # ── Additional: Cancel non-existent → 404 ────────────────────────────────
    async def test_cancel_nonexistent_appointment_returns_404(
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

    # ── Additional: List with admin lists all ────────────────────────────────
    async def test_admin_can_list_all_appointments_paginated(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        appts = [_appt_out() for _ in range(3)]
        page = PaginatedResponse(data=appts, total=3, page=1, page_size=20, total_pages=1)
        with patch(
            "domains.medai.services.appointment_service.AppointmentService.list_appointments",
            new=AsyncMock(return_value=page),
        ):
            resp = await async_client.get(BASE, headers=admin_headers)

        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 3

    # ── Additional: WebSocket event fired on book ─────────────────────────────
    async def test_websocket_event_fired_on_booking(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        """After successful booking, websocket notification must be attempted."""
        booked = _appt_out(patient_id=self._patient_id, doctor_id=self._doctor_id)
        no_conflict = MagicMock()
        no_conflict.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=no_conflict)

        with patch(
            "domains.medai.services.appointment_service.AppointmentService.create_appointment",
            new=AsyncMock(return_value=booked),
        ):
            with patch(
                "domains.medai.websockets.manager.manager.notify_appointment_event",
                new=AsyncMock(),
            ) as mock_notify:
                await async_client.post(
                    f"{BASE}/book",
                    json=self._payload(),
                    headers=patient_headers,
                )

        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args
        assert call_kwargs[0][0] == "appointment_created"
