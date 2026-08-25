"""
Unit tests for domains/medai/services/doctor_service.py
All database interactions are mocked – no real DB required.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domains.medai.schemas.doctor import DoctorCreate, DoctorOut, DoctorUpdate
from domains.medai.services.doctor_service import DoctorService

_NOW = datetime.now(timezone.utc)


def _make_mock_doctor(
    doctor_id: uuid.UUID | None = None,
    first_name: str = "John",
    last_name: str = "Smith",
    email: str = "dr.smith@clinic.com",
    specialty: str = "Cardiology",
) -> MagicMock:
    """Build a mock Doctor ORM object."""
    doc = MagicMock()
    doc.id = doctor_id or uuid.uuid4()
    doc.user_id = str(uuid.uuid4())
    doc.first_name = first_name
    doc.last_name = last_name
    doc.full_name = f"Dr. {first_name} {last_name}"
    doc.email = email
    doc.phone = "555-1234"
    doc.specialty = specialty
    doc.license_number = "LIC-001"
    doc.years_of_experience = 10
    doc.bio = None
    doc.consultation_fee = 150.0
    doc.available_days = "Mon,Tue,Wed"
    doc.working_hours_start = "09:00"
    doc.working_hours_end = "17:00"
    doc.is_available = True
    doc.is_deleted = False
    doc.created_at = _NOW
    doc.updated_at = _NOW
    return doc


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def doctor_service(mock_session: AsyncMock) -> DoctorService:
    return DoctorService(mock_session)


# ── create_doctor ─────────────────────────────────────────────────────────────

class TestCreateDoctor:
    async def test_create_doctor_returns_doctor_out(self, doctor_service: DoctorService):
        mock_doc = _make_mock_doctor()
        with patch.object(doctor_service.repo, "create", new=AsyncMock(return_value=mock_doc)):
            data = DoctorCreate(
                first_name="John",
                last_name="Smith",
                email="dr.smith@clinic.com",
                phone="555-1234",
                specialty="Cardiology",
                license_number="LIC-001",
            )
            result = await doctor_service.create_doctor(data)
        assert isinstance(result, DoctorOut)
        assert result.email == "dr.smith@clinic.com"

    async def test_create_doctor_calls_repo_create(self, doctor_service: DoctorService):
        mock_doc = _make_mock_doctor()
        mock_create = AsyncMock(return_value=mock_doc)
        with patch.object(doctor_service.repo, "create", new=mock_create):
            data = DoctorCreate(
                first_name="Jane",
                last_name="Doe",
                email="jane@clinic.com",
                phone="555-9999",
                specialty="Neurology",
                license_number="LIC-002",
            )
            await doctor_service.create_doctor(data)
        mock_create.assert_called_once()

    async def test_create_doctor_injects_user_id(self, doctor_service: DoctorService):
        """create_doctor should inject a generated user_id into the payload."""
        mock_doc = _make_mock_doctor()
        captured_payload: dict = {}

        async def _capture(payload):
            captured_payload.update(payload)
            return mock_doc

        with patch.object(doctor_service.repo, "create", new=_capture):
            data = DoctorCreate(
                first_name="Bob",
                last_name="Jones",
                email="bob@clinic.com",
                phone="555-0001",
                specialty="Dermatology",
                license_number="LIC-003",
            )
            await doctor_service.create_doctor(data)

        assert "user_id" in captured_payload


# ── get_doctor ────────────────────────────────────────────────────────────────

class TestGetDoctor:
    async def test_returns_doctor_out_when_found(self, doctor_service: DoctorService):
        mock_doc = _make_mock_doctor()
        with patch.object(doctor_service.repo, "get_by_id", new=AsyncMock(return_value=mock_doc)):
            result = await doctor_service.get_doctor(mock_doc.id)
        assert result is not None
        assert result.specialty == "Cardiology"

    async def test_returns_none_when_not_found(self, doctor_service: DoctorService):
        with patch.object(doctor_service.repo, "get_by_id", new=AsyncMock(return_value=None)):
            result = await doctor_service.get_doctor(uuid.uuid4())
        assert result is None


# ── list_doctors ──────────────────────────────────────────────────────────────

class TestListDoctors:
    async def test_pagination_total_pages_calculation(self, doctor_service: DoctorService):
        docs = [_make_mock_doctor() for _ in range(3)]
        with patch.object(doctor_service.repo, "list", new=AsyncMock(return_value=(docs, 25))):
            result = await doctor_service.list_doctors(page=1, page_size=10)
        assert result.total == 25
        assert result.total_pages == 3  # ceil(25/10)

    async def test_pagination_exact_division(self, doctor_service: DoctorService):
        docs = [_make_mock_doctor() for _ in range(5)]
        with patch.object(doctor_service.repo, "list", new=AsyncMock(return_value=(docs, 20))):
            result = await doctor_service.list_doctors(page=1, page_size=5)
        assert result.total_pages == 4

    async def test_data_is_mapped_to_doctor_out(self, doctor_service: DoctorService):
        docs = [_make_mock_doctor(first_name="Alice"), _make_mock_doctor(first_name="Bob")]
        with patch.object(doctor_service.repo, "list", new=AsyncMock(return_value=(docs, 2))):
            result = await doctor_service.list_doctors()
        assert len(result.data) == 2
        assert all(isinstance(d, DoctorOut) for d in result.data)


# ── update_doctor ─────────────────────────────────────────────────────────────

class TestUpdateDoctor:
    async def test_returns_updated_doctor(self, doctor_service: DoctorService):
        updated_doc = _make_mock_doctor(specialty="Oncology")
        with patch.object(doctor_service.repo, "update", new=AsyncMock(return_value=updated_doc)):
            result = await doctor_service.update_doctor(uuid.uuid4(), DoctorUpdate(specialty="Oncology"))
        assert result is not None
        assert result.specialty == "Oncology"

    async def test_returns_none_when_not_found(self, doctor_service: DoctorService):
        with patch.object(doctor_service.repo, "update", new=AsyncMock(return_value=None)):
            result = await doctor_service.update_doctor(uuid.uuid4(), DoctorUpdate())
        assert result is None


# ── delete_doctor ─────────────────────────────────────────────────────────────

class TestDeleteDoctor:
    async def test_delete_delegates_to_soft_delete(self, doctor_service: DoctorService):
        mock_delete = AsyncMock(return_value=True)
        with patch.object(doctor_service.repo, "soft_delete", new=mock_delete):
            result = await doctor_service.delete_doctor(uuid.uuid4())
        assert result is True
        mock_delete.assert_called_once()

    async def test_delete_returns_false_when_not_found(self, doctor_service: DoctorService):
        with patch.object(doctor_service.repo, "soft_delete", new=AsyncMock(return_value=False)):
            result = await doctor_service.delete_doctor(uuid.uuid4())
        assert result is False


# ── search / available ────────────────────────────────────────────────────────

class TestSearchDoctors:
    async def test_search_returns_mapped_list(self, doctor_service: DoctorService):
        docs = [_make_mock_doctor()]
        with patch.object(doctor_service.repo, "search", new=AsyncMock(return_value=docs)):
            result = await doctor_service.search_doctors("cardio")
        assert len(result) == 1
        assert isinstance(result[0], DoctorOut)

    async def test_get_available_passes_specialty(self, doctor_service: DoctorService):
        docs = [_make_mock_doctor()]
        mock_available = AsyncMock(return_value=docs)
        with patch.object(doctor_service.repo, "get_available", new=mock_available):
            await doctor_service.get_available_doctors(specialty="Cardiology")
        mock_available.assert_called_once_with("Cardiology")
