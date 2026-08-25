"""
Unit tests for domains/medai/services/appointment_service.py
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domains.medai.schemas.appointment import (
    AppointmentCreate,
    AppointmentOut,
    AppointmentUpdate,
)
from domains.medai.services.appointment_service import AppointmentService

_NOW = datetime.now(timezone.utc)


def _make_mock_appt(
    appt_id: uuid.UUID | None = None,
    status: str = "scheduled",
) -> MagicMock:
    appt = MagicMock()
    appt.id = appt_id or uuid.uuid4()
    appt.patient_id = uuid.uuid4()
    appt.doctor_id = uuid.uuid4()
    appt.appointment_type = "consultation"
    appt.status = status
    appt.scheduled_at = datetime.now(timezone.utc)
    appt.duration_minutes = 30
    appt.reason = None
    appt.notes = None
    appt.ai_triage_summary = None
    appt.is_deleted = False
    appt.created_at = _NOW
    appt.updated_at = _NOW
    return appt


@pytest.fixture
def appt_service() -> AppointmentService:
    return AppointmentService(AsyncMock())


class TestCreateAppointment:
    async def test_returns_appointment_out(self, appt_service: AppointmentService):
        mock_appt = _make_mock_appt()
        with patch.object(appt_service.repo, "create", new=AsyncMock(return_value=mock_appt)):
            data = AppointmentCreate(
                patient_id=uuid.uuid4(),
                doctor_id=uuid.uuid4(),
                scheduled_at=datetime.now(timezone.utc),
            )
            result = await appt_service.create_appointment(data)
        assert isinstance(result, AppointmentOut)

    async def test_patient_and_doctor_ids_are_strings_in_payload(self, appt_service: AppointmentService):
        """patient_id and doctor_id must be serialised as strings for the DB."""
        captured: dict = {}

        async def _capture(payload):
            captured.update(payload)
            return _make_mock_appt()

        with patch.object(appt_service.repo, "create", new=_capture):
            patient_id = uuid.uuid4()
            doctor_id = uuid.uuid4()
            data = AppointmentCreate(
                patient_id=patient_id,
                doctor_id=doctor_id,
                scheduled_at=datetime.now(timezone.utc),
            )
            await appt_service.create_appointment(data)

        assert captured["patient_id"] == str(patient_id)
        assert captured["doctor_id"] == str(doctor_id)


class TestGetAppointment:
    async def test_returns_appointment_out_when_found(self, appt_service: AppointmentService):
        mock_appt = _make_mock_appt()
        with patch.object(appt_service.repo, "get_by_id", new=AsyncMock(return_value=mock_appt)):
            result = await appt_service.get_appointment(mock_appt.id)
        assert result is not None

    async def test_returns_none_when_not_found(self, appt_service: AppointmentService):
        with patch.object(appt_service.repo, "get_by_id", new=AsyncMock(return_value=None)):
            result = await appt_service.get_appointment(uuid.uuid4())
        assert result is None


class TestListAppointments:
    async def test_pagination_total_pages(self, appt_service: AppointmentService):
        appts = [_make_mock_appt() for _ in range(5)]
        with patch.object(appt_service.repo, "list", new=AsyncMock(return_value=(appts, 45))):
            result = await appt_service.list_appointments(page=2, page_size=20)
        assert result.total == 45
        assert result.total_pages == 3  # ceil(45/20)
        assert result.page == 2

    async def test_offset_calculation(self, appt_service: AppointmentService):
        mock_list = AsyncMock(return_value=([], 0))
        with patch.object(appt_service.repo, "list", new=mock_list):
            await appt_service.list_appointments(page=3, page_size=10)
        # page=3, page_size=10 → offset = (3-1)*10 = 20
        mock_list.assert_called_once_with(offset=20, limit=10, order_by="scheduled_at", descending=False)


class TestCancelAppointment:
    async def test_cancel_sends_cancelled_status(self, appt_service: AppointmentService):
        mock_appt = _make_mock_appt(status="cancelled")
        mock_update = AsyncMock(return_value=mock_appt)
        with patch.object(appt_service.repo, "update", new=mock_update):
            result = await appt_service.cancel_appointment(uuid.uuid4())
        mock_update.assert_called_once()
        call_args = mock_update.call_args[0]
        assert call_args[1] == {"status": "cancelled"}
        assert result is not None

    async def test_cancel_returns_none_when_not_found(self, appt_service: AppointmentService):
        with patch.object(appt_service.repo, "update", new=AsyncMock(return_value=None)):
            result = await appt_service.cancel_appointment(uuid.uuid4())
        assert result is None


class TestGetUpcoming:
    async def test_returns_list_of_appointment_out(self, appt_service: AppointmentService):
        appts = [_make_mock_appt(), _make_mock_appt()]
        with patch.object(appt_service.repo, "get_upcoming", new=AsyncMock(return_value=appts)):
            result = await appt_service.get_upcoming()
        assert len(result) == 2
        assert all(isinstance(a, AppointmentOut) for a in result)


class TestGetByPatient:
    async def test_filters_by_patient_id(self, appt_service: AppointmentService):
        pid = str(uuid.uuid4())
        appts = [_make_mock_appt()]
        mock_get = AsyncMock(return_value=appts)
        with patch.object(appt_service.repo, "get_by_patient", new=mock_get):
            await appt_service.get_by_patient(pid)
        mock_get.assert_called_once_with(pid)
