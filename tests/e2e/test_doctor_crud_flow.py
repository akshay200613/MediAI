"""
E2E tests – full Doctor CRUD flow.

These tests simulate an admin user performing a complete lifecycle:
  1. Create a doctor (POST /doctors)
  2. Read it back  (GET  /doctors/{id})
  3. Update it      (PATCH /doctors/{id})
  4. Delete it      (DELETE /doctors/{id})
  5. Verify 404     (GET  /doctors/{id} → 404)

All DB interactions are mocked via the `async_client` fixture
which injects the mock session. Service calls are patched per step.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from domains.medai.schemas.doctor import DoctorOut

_NOW = datetime.now(timezone.utc)


def _build_doctor(
    doctor_id: uuid.UUID,
    specialty: str = "Cardiology",
    is_deleted: bool = False,
) -> DoctorOut:
    return DoctorOut(
        id=doctor_id,
        first_name="E2E",
        last_name="Doctor",
        full_name="Dr. E2E Doctor",
        email="e2e.doctor@clinic.com",
        phone="555-E2E0",
        specialty=specialty,
        license_number="LIC-E2E",
        years_of_experience=5,
        bio="E2E test doctor",
        consultation_fee=100.0,
        available_days="Mon,Fri",
        working_hours_start="08:00",
        working_hours_end="16:00",
        is_available=True,
        is_deleted=is_deleted,
        created_at=_NOW,
        updated_at=_NOW,
    )


CREATE_PAYLOAD = {
    "first_name": "E2E",
    "last_name": "Doctor",
    "email": "e2e.doctor@clinic.com",
    "phone": "555-E2E0",
    "specialty": "Cardiology",
    "license_number": "LIC-E2E",
    "years_of_experience": 5,
    "bio": "E2E test doctor",
    "consultation_fee": 100.0,
}

BASE = "/api/v1/medai/doctors"


class TestDoctorCRUDFlow:
    async def test_full_crud_lifecycle(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        doctor_id = uuid.uuid4()

        # 1. CREATE ──────────────────────────────────────────────────────────
        created_doc = _build_doctor(doctor_id)
        with patch(
            "domains.medai.services.doctor_service.DoctorService.create_doctor",
            new=AsyncMock(return_value=created_doc),
        ):
            create_resp = await async_client.post(
                BASE, json=CREATE_PAYLOAD, headers=admin_headers
            )
        assert create_resp.status_code == 201, f"Create failed: {create_resp.text}"
        create_body = create_resp.json()
        assert create_body["data"]["specialty"] == "Cardiology"
        assert create_body["success"] is True

        # 2. READ ─────────────────────────────────────────────────────────────
        with patch(
            "domains.medai.services.doctor_service.DoctorService.get_doctor",
            new=AsyncMock(return_value=created_doc),
        ):
            get_resp = await async_client.get(
                f"{BASE}/{doctor_id}", headers=admin_headers
            )
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["license_number"] == "LIC-E2E"

        # 3. UPDATE ───────────────────────────────────────────────────────────
        updated_doc = _build_doctor(doctor_id, specialty="Oncology")
        with patch(
            "domains.medai.services.doctor_service.DoctorService.update_doctor",
            new=AsyncMock(return_value=updated_doc),
        ):
            patch_resp = await async_client.patch(
                f"{BASE}/{doctor_id}",
                json={"specialty": "Oncology"},
                headers=admin_headers,
            )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["data"]["specialty"] == "Oncology"

        # 4. DELETE ───────────────────────────────────────────────────────────
        with patch(
            "domains.medai.services.doctor_service.DoctorService.delete_doctor",
            new=AsyncMock(return_value=True),
        ):
            del_resp = await async_client.delete(
                f"{BASE}/{doctor_id}", headers=admin_headers
            )
        assert del_resp.status_code == 204

        # 5. VERIFY 404 ───────────────────────────────────────────────────────
        with patch(
            "domains.medai.services.doctor_service.DoctorService.get_doctor",
            new=AsyncMock(return_value=None),
        ):
            miss_resp = await async_client.get(
                f"{BASE}/{doctor_id}", headers=admin_headers
            )
        assert miss_resp.status_code == 404
