"""
Integration tests – appointment concurrency and edge-case booking scenarios.

Focuses on the double-booking guard, slot listing, and boundary conditions
in POST /api/v1/medai/appointments/book and GET /booked-slots.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from domains.medai.schemas.appointment import AppointmentOut

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
        reason=None,
        notes=None,
        ai_triage_summary=None,
        is_deleted=False,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _book_payload(
    patient_id: uuid.UUID,
    doctor_id: uuid.UUID,
    scheduled_at: datetime | None = None,
) -> dict:
    dt = scheduled_at or datetime.now(timezone.utc)
    return {
        "patient_id": str(patient_id),
        "doctor_id": str(doctor_id),
        "scheduled_at": dt.isoformat(),
        "appointment_type": "consultation",
        "duration_minutes": 30,
    }


# ─── Double-booking guard ─────────────────────────────────────────────────────

class TestDoubleBookingPrevention:
    async def test_first_booking_succeeds(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        """When no conflicting appointment exists, booking returns 201."""
        pid, did = uuid.uuid4(), uuid.uuid4()
        appt = _appt_out(patient_id=pid, doctor_id=did)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No existing booking
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
                    json=_book_payload(pid, did),
                    headers=patient_headers,
                )

        assert resp.status_code == 201
        assert resp.json()["data"]["status"] == "scheduled"

    async def test_second_booking_same_slot_returns_409(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        """Second booking at the identical doctor+time slot → 409 Conflict."""
        pid, did = uuid.uuid4(), uuid.uuid4()

        # Simulate an existing appointment
        existing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute = AsyncMock(return_value=mock_result)

        resp = await async_client.post(
            f"{BASE}/book",
            json=_book_payload(pid, did),
            headers=patient_headers,
        )

        assert resp.status_code == 409
        assert "double booking" in resp.json()["detail"].lower()

    async def test_booking_different_time_slot_same_doctor_succeeds(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        """Two bookings with different times for the same doctor must both succeed."""
        pid, did = uuid.uuid4(), uuid.uuid4()
        slot1 = datetime.now(timezone.utc)
        slot2 = slot1 + timedelta(hours=1)

        appt1 = _appt_out(patient_id=pid, doctor_id=did, scheduled_at=slot1)

        # No conflict for slot2
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "domains.medai.services.appointment_service.AppointmentService.create_appointment",
            new=AsyncMock(return_value=appt1),
        ):
            with patch("domains.medai.websockets.manager.manager.notify_appointment_event", new=AsyncMock()):
                resp = await async_client.post(
                    f"{BASE}/book",
                    json=_book_payload(pid, did, slot2),
                    headers=patient_headers,
                )

        assert resp.status_code == 201

    async def test_booking_at_cancelled_slot_is_allowed(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        """A cancelled appointment frees up the slot – booking should succeed."""
        pid, did = uuid.uuid4(), uuid.uuid4()
        appt = _appt_out(patient_id=pid, doctor_id=did, status="scheduled")

        # Cancelled appointments are excluded from the double-booking query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # Query excludes CANCELLED
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "domains.medai.services.appointment_service.AppointmentService.create_appointment",
            new=AsyncMock(return_value=appt),
        ):
            with patch("domains.medai.websockets.manager.manager.notify_appointment_event", new=AsyncMock()):
                resp = await async_client.post(
                    f"{BASE}/book",
                    json=_book_payload(pid, did),
                    headers=patient_headers,
                )

        assert resp.status_code == 201

    async def test_booking_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.post(
            f"{BASE}/book",
            json=_book_payload(uuid.uuid4(), uuid.uuid4()),
        )
        assert resp.status_code in (401, 403)


# ─── GET /booked-slots ────────────────────────────────────────────────────────

class TestBookedSlotsEndpoint:
    async def test_booked_slots_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.get(
            f"{BASE}/booked-slots",
            params={"doctor_id": str(uuid.uuid4()), "date": "2025-01-15"},
        )
        assert resp.status_code in (401, 403)

    async def test_booked_slots_returns_list(
        self, async_client: AsyncClient, doctor_headers: dict, mock_session: AsyncMock
    ):
        """Returns a list of ISO datetime strings for booked slots."""
        slot_dt = datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc)
        mock_scalars = MagicMock()
        mock_scalars.scalars.return_value = [slot_dt]
        mock_session.execute = AsyncMock(return_value=mock_scalars)

        resp = await async_client.get(
            f"{BASE}/booked-slots",
            params={"doctor_id": str(uuid.uuid4()), "date": "2025-01-15"},
            headers=doctor_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["data"], list)

    async def test_booked_slots_empty_when_no_bookings(
        self, async_client: AsyncClient, doctor_headers: dict, mock_session: AsyncMock
    ):
        """Empty result when no appointments exist on that date."""
        mock_scalars = MagicMock()
        mock_scalars.scalars.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_scalars)

        resp = await async_client.get(
            f"{BASE}/booked-slots",
            params={"doctor_id": str(uuid.uuid4()), "date": "2025-12-31"},
            headers=doctor_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    async def test_booked_slots_invalid_date_returns_400(
        self, async_client: AsyncClient, doctor_headers: dict
    ):
        """date param in wrong format → 400."""
        resp = await async_client.get(
            f"{BASE}/booked-slots",
            params={"doctor_id": str(uuid.uuid4()), "date": "15-01-2025"},
            headers=doctor_headers,
        )
        assert resp.status_code == 400

    async def test_booked_slots_patient_can_access(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        """Patients (with VIEW_APPOINTMENT permission) can also query booked slots."""
        mock_scalars = MagicMock()
        mock_scalars.scalars.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_scalars)

        resp = await async_client.get(
            f"{BASE}/booked-slots",
            params={"doctor_id": str(uuid.uuid4()), "date": "2025-06-01"},
            headers=patient_headers,
        )
        assert resp.status_code == 200


# ─── Concurrent-style sequential tests ───────────────────────────────────────

class TestConcurrentBookingSimulation:
    async def test_first_wins_second_loses_sequential(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        """
        Simulate two requests for the same slot arriving one after the other.
        First sees no existing booking → 201.
        Second sees the existing booking → 409.
        """
        pid, did = uuid.uuid4(), uuid.uuid4()
        slot = datetime.now(timezone.utc)
        appt = _appt_out(patient_id=pid, doctor_id=did, scheduled_at=slot)

        # First request: no conflict
        free_result = MagicMock()
        free_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=free_result)

        with patch(
            "domains.medai.services.appointment_service.AppointmentService.create_appointment",
            new=AsyncMock(return_value=appt),
        ):
            with patch("domains.medai.websockets.manager.manager.notify_appointment_event", new=AsyncMock()):
                resp1 = await async_client.post(
                    f"{BASE}/book",
                    json=_book_payload(pid, did, slot),
                    headers=patient_headers,
                )

        assert resp1.status_code == 201

        # Second request: conflict exists
        conflict_result = MagicMock()
        conflict_result.scalar_one_or_none.return_value = MagicMock()
        mock_session.execute = AsyncMock(return_value=conflict_result)

        resp2 = await async_client.post(
            f"{BASE}/book",
            json=_book_payload(uuid.uuid4(), did, slot),
            headers=patient_headers,
        )
        assert resp2.status_code == 409
