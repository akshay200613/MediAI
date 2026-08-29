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


# ─── Double-booking and Slot Capacity guard ──────────────────────────────────

class TestDoubleBookingPrevention:
    async def test_first_booking_succeeds(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        """When slot capacity and patient limit are not exceeded, booking returns 201."""
        pid, did = uuid.uuid4(), uuid.uuid4()
        appt = _appt_out(patient_id=pid, doctor_id=did)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []  # No existing booking
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
                    json=_book_payload(pid, did),
                    headers=patient_headers,
                )

        assert resp.status_code == 201
        assert resp.json()["data"]["status"] == "scheduled"

    async def test_slot_capacity_exceeded_returns_409(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        """When slot already has 2 bookings (max capacity reached), booking returns 409 Conflict."""
        pid, did = uuid.uuid4(), uuid.uuid4()

        # Simulate 2 existing appointments at this slot
        existing1 = MagicMock(doctor_id=str(did), patient_id=str(uuid.uuid4()))
        existing2 = MagicMock(doctor_id=str(did), patient_id=str(uuid.uuid4()))
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing1, existing2]
        mock_result.scalar_one_or_none.return_value = existing1
        mock_session.execute = AsyncMock(return_value=mock_result)

        resp = await async_client.post(
            f"{BASE}/book",
            json=_book_payload(pid, did),
            headers=patient_headers,
        )

        assert resp.status_code == 409
        assert "slot booking limit" in resp.json()["detail"].lower() or "limit" in resp.json()["detail"].lower()

    async def test_patient_limit_exceeded_returns_409(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        """When patient already has 2 active appointments, booking a 3rd returns 409 Conflict."""
        pid, did = uuid.uuid4(), uuid.uuid4()

        # Simulate 2 existing active appointments for this patient
        existing1 = MagicMock(doctor_id=str(uuid.uuid4()), patient_id=str(pid))
        existing2 = MagicMock(doctor_id=str(uuid.uuid4()), patient_id=str(pid))
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing1, existing2]
        mock_result.scalar_one_or_none.return_value = existing1
        mock_session.execute = AsyncMock(return_value=mock_result)

        resp = await async_client.post(
            f"{BASE}/book",
            json=_book_payload(pid, did),
            headers=patient_headers,
        )

        assert resp.status_code == 409
        assert "booking limit reached" in resp.json()["detail"].lower() or "active appointment" in resp.json()["detail"].lower()

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
        mock_result.scalars.return_value.all.return_value = []
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

        # Cancelled appointments are excluded from active checks
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar_one_or_none.return_value = None
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

    async def test_booked_slots_returns_only_full_slots(
        self, async_client: AsyncClient, doctor_headers: dict, mock_session: AsyncMock
    ):
        """Returns slots that have reached maximum capacity (2 bookings)."""
        slot_full = datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc)
        slot_partial = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)

        # slot_full has 2 bookings (full), slot_partial has 1 booking (still open)
        mock_scalars = MagicMock()
        mock_scalars.scalars.return_value.all.return_value = [slot_full, slot_full, slot_partial]
        mock_session.execute = AsyncMock(return_value=mock_scalars)

        resp = await async_client.get(
            f"{BASE}/booked-slots",
            params={"doctor_id": str(uuid.uuid4()), "date": "2025-01-15"},
            headers=doctor_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["data"], list)
        assert slot_full.isoformat() in body["data"]
        assert slot_partial.isoformat() not in body["data"]

    async def test_booked_slots_empty_when_no_bookings(
        self, async_client: AsyncClient, doctor_headers: dict, mock_session: AsyncMock
    ):
        """Empty result when no appointments exist on that date."""
        mock_scalars = MagicMock()
        mock_scalars.scalars.return_value.all.return_value = []
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
        mock_scalars.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_scalars)

        resp = await async_client.get(
            f"{BASE}/booked-slots",
            params={"doctor_id": str(uuid.uuid4()), "date": "2025-06-01"},
            headers=patient_headers,
        )
        assert resp.status_code == 200


# ─── Concurrent-style sequential tests ───────────────────────────────────────

class TestConcurrentBookingSimulation:
    async def test_slot_capacity_reaches_limit_sequential(
        self, async_client: AsyncClient, patient_headers: dict, mock_session: AsyncMock
    ):
        """
        Simulate requests for the same slot arriving sequentially.
        When capacity is 2, the 3rd booking fails with 409.
        """
        did = uuid.uuid4()
        slot = datetime.now(timezone.utc)
        appt1 = _appt_out(patient_id=uuid.uuid4(), doctor_id=did, scheduled_at=slot)

        # First request: capacity available
        free_result = MagicMock()
        free_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=free_result)

        with patch(
            "domains.medai.services.appointment_service.AppointmentService.create_appointment",
            new=AsyncMock(return_value=appt1),
        ):
            with patch("domains.medai.websockets.manager.manager.notify_appointment_event", new=AsyncMock()):
                resp1 = await async_client.post(
                    f"{BASE}/book",
                    json=_book_payload(uuid.uuid4(), did, slot),
                    headers=patient_headers,
                )

        assert resp1.status_code == 201

        # 3rd request: 2 existing bookings already fill the slot
        existing1 = MagicMock(doctor_id=str(did), scheduled_at=slot)
        existing2 = MagicMock(doctor_id=str(did), scheduled_at=slot)
        full_result = MagicMock()
        full_result.scalars.return_value.all.return_value = [existing1, existing2]
        full_result.scalar_one_or_none.return_value = existing1
        mock_session.execute = AsyncMock(return_value=full_result)

        resp3 = await async_client.post(
            f"{BASE}/book",
            json=_book_payload(uuid.uuid4(), did, slot),
            headers=patient_headers,
        )
        assert resp3.status_code == 409

