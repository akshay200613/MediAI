"""
Unit tests for Patient Service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import uuid

from domains.medai.services.patient_service import PatientService
from domains.medai.schemas.patient import PatientCreate, PatientUpdate


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def patient_service(mock_session):
    return PatientService(mock_session)


@pytest.fixture
def sample_patient_create():
    return PatientCreate(
        first_name="John",
        last_name="Doe",
        phone="+1234567890",
        email="john.doe@example.com",
        gender="male",
    )


@pytest.mark.asyncio
async def test_create_patient(patient_service, sample_patient_create):
    """Test patient creation calls repository correctly."""
    mock_patient = MagicMock()
    mock_patient.id = uuid.uuid4()
    mock_patient.first_name = "John"
    mock_patient.last_name = "Doe"
    mock_patient.full_name = "John Doe"
    mock_patient.email = "john.doe@example.com"
    mock_patient.phone = "+1234567890"
    mock_patient.date_of_birth = None
    mock_patient.gender = "male"
    mock_patient.blood_group = None
    mock_patient.address = None
    mock_patient.city = None
    mock_patient.allergies = None
    mock_patient.chronic_conditions = None
    mock_patient.is_deleted = False
    from datetime import datetime
    mock_patient.created_at = datetime.now()
    mock_patient.updated_at = datetime.now()

    patient_service.repo.create = AsyncMock(return_value=mock_patient)
    result = await patient_service.create_patient(sample_patient_create)

    patient_service.repo.create.assert_called_once()
    assert result.first_name == "John"


@pytest.mark.asyncio
async def test_get_patient_not_found(patient_service):
    """Test get_patient returns None for nonexistent ID."""
    patient_service.repo.get_by_id = AsyncMock(return_value=None)
    result = await patient_service.get_patient(uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_delete_patient(patient_service):
    """Test soft delete delegates to repo."""
    patient_service.repo.soft_delete = AsyncMock(return_value=True)
    result = await patient_service.delete_patient(uuid.uuid4())
    assert result is True
