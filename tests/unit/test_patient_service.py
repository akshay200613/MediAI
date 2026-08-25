"""
Unit tests for domains/medai/services/patient_service.py
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domains.medai.schemas.patient import PatientCreate, PatientOut, PatientUpdate
from domains.medai.services.patient_service import PatientService

_NOW = datetime.now(timezone.utc)


def _make_mock_patient(
    patient_id: uuid.UUID | None = None,
    user_id: str | None = None,
    email: str = "patient@test.com",
    is_deleted: bool = False,
) -> MagicMock:
    p = MagicMock()
    p.id = patient_id or uuid.uuid4()
    p.user_id = user_id or str(uuid.uuid4())
    p.first_name = "Alice"
    p.last_name = "Doe"
    p.full_name = "Alice Doe"
    p.email = email
    p.phone = "555-0001"
    p.date_of_birth = None
    p.gender = None
    p.blood_group = None
    p.address = None
    p.city = None
    p.state = None
    p.allergies = None
    p.chronic_conditions = None
    p.emergency_contact_name = None
    p.emergency_contact_phone = None
    p.is_deleted = is_deleted
    p.created_at = _NOW
    p.updated_at = _NOW
    return p


@pytest.fixture
def patient_service() -> PatientService:
    return PatientService(AsyncMock())


class TestCreatePatient:
    async def test_create_returns_patient_out(self, patient_service: PatientService):
        mock_patient = _make_mock_patient()
        with patch.object(patient_service.repo, "create", new=AsyncMock(return_value=mock_patient)):
            data = PatientCreate(
                first_name="Alice",
                last_name="Doe",
                email="alice@test.com",
                phone="555-0001",
            )
            result = await patient_service.create_patient(data)
        assert isinstance(result, PatientOut)

    async def test_create_calls_repo_with_dumped_data(self, patient_service: PatientService):
        mock_patient = _make_mock_patient()
        mock_create = AsyncMock(return_value=mock_patient)
        with patch.object(patient_service.repo, "create", new=mock_create):
            data = PatientCreate(
                first_name="Bob",
                last_name="Smith",
                email="bob@test.com",
                phone="555-1111",
            )
            await patient_service.create_patient(data)
        mock_create.assert_called_once()


class TestGetPatient:
    async def test_returns_patient_out_when_found(self, patient_service: PatientService):
        mock_patient = _make_mock_patient()
        with patch.object(patient_service.repo, "get_by_id", new=AsyncMock(return_value=mock_patient)):
            result = await patient_service.get_patient(mock_patient.id)
        assert result is not None

    async def test_returns_none_when_missing(self, patient_service: PatientService):
        with patch.object(patient_service.repo, "get_by_id", new=AsyncMock(return_value=None)):
            result = await patient_service.get_patient(uuid.uuid4())
        assert result is None


class TestGetPatientByUserId:
    async def test_returns_patient_when_user_id_matches(self, patient_service: PatientService):
        uid = str(uuid.uuid4())
        mock_patient = _make_mock_patient(user_id=uid)
        with patch.object(patient_service.repo, "get_by_user_id", new=AsyncMock(return_value=mock_patient)):
            result = await patient_service.get_patient_by_user_id(uid)
        assert result is not None

    async def test_falls_back_to_email_lookup(self, patient_service: PatientService):
        """When user_id lookup fails, should try email fallback."""
        uid = str(uuid.uuid4())
        email = "fallback@test.com"
        mock_patient = _make_mock_patient(email=email, is_deleted=False)

        # user_id lookup → None; email lookup → patient
        with patch.object(patient_service.repo, "get_by_user_id", new=AsyncMock(return_value=None)):
            with patch.object(patient_service.repo, "get_by_field", new=AsyncMock(return_value=mock_patient)):
                result = await patient_service.get_patient_by_user_id(uid, user_email=email)
        assert result is not None

    async def test_email_fallback_ignored_for_deleted_patient(self, patient_service: PatientService):
        uid = str(uuid.uuid4())
        email = "deleted@test.com"
        deleted_patient = _make_mock_patient(email=email, is_deleted=True)

        with patch.object(patient_service.repo, "get_by_user_id", new=AsyncMock(return_value=None)):
            with patch.object(patient_service.repo, "get_by_field", new=AsyncMock(return_value=deleted_patient)):
                result = await patient_service.get_patient_by_user_id(uid, user_email=email)
        assert result is None

    async def test_returns_none_when_no_match(self, patient_service: PatientService):
        with patch.object(patient_service.repo, "get_by_user_id", new=AsyncMock(return_value=None)):
            with patch.object(patient_service.repo, "get_by_field", new=AsyncMock(return_value=None)):
                result = await patient_service.get_patient_by_user_id("uid-x", user_email="no@test.com")
        assert result is None


class TestListPatients:
    async def test_pagination_total_pages(self, patient_service: PatientService):
        patients = [_make_mock_patient() for _ in range(3)]
        with patch.object(patient_service.repo, "list", new=AsyncMock(return_value=(patients, 30))):
            result = await patient_service.list_patients(page=1, page_size=10)
        assert result.total_pages == 3
        assert result.total == 30

    async def test_single_page_when_total_less_than_page_size(self, patient_service: PatientService):
        patients = [_make_mock_patient()]
        with patch.object(patient_service.repo, "list", new=AsyncMock(return_value=(patients, 5))):
            result = await patient_service.list_patients(page=1, page_size=20)
        assert result.total_pages == 1


class TestDeletePatient:
    async def test_delete_returns_true(self, patient_service: PatientService):
        with patch.object(patient_service.repo, "soft_delete", new=AsyncMock(return_value=True)):
            result = await patient_service.delete_patient(uuid.uuid4())
        assert result is True

    async def test_delete_returns_false_when_not_found(self, patient_service: PatientService):
        with patch.object(patient_service.repo, "soft_delete", new=AsyncMock(return_value=False)):
            result = await patient_service.delete_patient(uuid.uuid4())
        assert result is False


class TestSearchPatients:
    async def test_search_maps_to_patient_out(self, patient_service: PatientService):
        patients = [_make_mock_patient(), _make_mock_patient()]
        with patch.object(patient_service.repo, "search", new=AsyncMock(return_value=patients)):
            result = await patient_service.search_patients("Alice")
        assert len(result) == 2
        assert all(isinstance(p, PatientOut) for p in result)
