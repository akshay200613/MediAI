"""
Integration tests for domains/medai/api/v1/doctors.py
Tests the full HTTP layer: routing, auth guards, request validation, and response shapes.
Uses AsyncClient with mock DB session – no real database needed.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from core.schemas.base import DataResponse, PaginatedResponse
from domains.medai.schemas.doctor import DoctorOut

_NOW = datetime.now(timezone.utc)


def _doctor_out(
    doctor_id: uuid.UUID | None = None,
    specialty: str = "Cardiology",
) -> DoctorOut:
    did = doctor_id or uuid.uuid4()
    return DoctorOut(
        id=did,
        first_name="John",
        last_name="Smith",
        full_name="Dr. John Smith",
        email="dr.smith@clinic.com",
        phone="555-1234",
        specialty=specialty,
        license_number="LIC-001",
        years_of_experience=10,
        bio=None,
        consultation_fee=150.0,
        available_days="Mon,Tue",
        working_hours_start="09:00",
        working_hours_end="17:00",
        is_available=True,
        is_deleted=False,
        created_at=_NOW,
        updated_at=_NOW,
    )


BASE = "/api/v1/medai/doctors"


# ── List Doctors ──────────────────────────────────────────────────────────────

class TestListDoctors:
    async def test_list_doctors_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.get(BASE)
        assert resp.status_code in (401, 403)

    async def test_list_doctors_with_auth_returns_200(
        self, async_client: AsyncClient, patient_headers: dict
    ):
        page = PaginatedResponse(
            data=[_doctor_out()],
            total=1, page=1, page_size=20, total_pages=1,
        )
        with patch(
            "domains.medai.services.doctor_service.DoctorService.list_doctors",
            new=AsyncMock(return_value=page),
        ):
            resp = await async_client.get(BASE, headers=patient_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert body["total"] == 1

    async def test_search_query_param_triggers_search(
        self, async_client: AsyncClient, patient_headers: dict
    ):
        with patch(
            "domains.medai.services.doctor_service.DoctorService.search_doctors",
            new=AsyncMock(return_value=[_doctor_out()]),
        ):
            resp = await async_client.get(
                f"{BASE}?search=cardio", headers=patient_headers
            )
        assert resp.status_code == 200

    async def test_available_only_filter(
        self, async_client: AsyncClient, patient_headers: dict
    ):
        with patch(
            "domains.medai.services.doctor_service.DoctorService.get_available_doctors",
            new=AsyncMock(return_value=[_doctor_out()]),
        ):
            resp = await async_client.get(
                f"{BASE}?available_only=true", headers=patient_headers
            )
        assert resp.status_code == 200


# ── Create Doctor ─────────────────────────────────────────────────────────────

class TestCreateDoctor:
    _payload = {
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane.doe@clinic.com",
        "phone": "555-9876",
        "specialty": "Neurology",
        "license_number": "LIC-999",
        "years_of_experience": 5,
        "consultation_fee": 200.0,
    }

    async def test_create_doctor_requires_admin_role(
        self, async_client: AsyncClient, patient_headers: dict
    ):
        resp = await async_client.post(BASE, json=self._payload, headers=patient_headers)
        assert resp.status_code == 403

    async def test_create_doctor_with_admin_role_returns_201(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        created = _doctor_out(specialty="Neurology")
        with patch(
            "domains.medai.services.doctor_service.DoctorService.create_doctor",
            new=AsyncMock(return_value=created),
        ):
            resp = await async_client.post(
                BASE, json=self._payload, headers=admin_headers
            )
        assert resp.status_code == 201
        body = resp.json()
        assert body["success"] is True

    async def test_create_doctor_validates_email(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        bad_payload = {**self._payload, "email": "not-an-email"}
        resp = await async_client.post(BASE, json=bad_payload, headers=admin_headers)
        assert resp.status_code == 422

    async def test_create_doctor_requires_token(self, async_client: AsyncClient):
        resp = await async_client.post(BASE, json=self._payload)
        assert resp.status_code in (401, 403)


# ── Get Doctor by ID ──────────────────────────────────────────────────────────

class TestGetDoctor:
    async def test_get_known_doctor_returns_200(
        self, async_client: AsyncClient, patient_headers: dict
    ):
        did = uuid.uuid4()
        doc = _doctor_out(doctor_id=did)
        with patch(
            "domains.medai.services.doctor_service.DoctorService.get_doctor",
            new=AsyncMock(return_value=doc),
        ):
            resp = await async_client.get(f"{BASE}/{did}", headers=patient_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["specialty"] == "Cardiology"

    async def test_get_unknown_doctor_returns_404(
        self, async_client: AsyncClient, patient_headers: dict
    ):
        with patch(
            "domains.medai.services.doctor_service.DoctorService.get_doctor",
            new=AsyncMock(return_value=None),
        ):
            resp = await async_client.get(f"{BASE}/{uuid.uuid4()}", headers=patient_headers)
        assert resp.status_code == 404

    async def test_get_doctor_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.get(f"{BASE}/{uuid.uuid4()}")
        assert resp.status_code in (401, 403)


# ── Update Doctor ─────────────────────────────────────────────────────────────

class TestUpdateDoctor:
    async def test_update_doctor_with_admin_returns_200(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        did = uuid.uuid4()
        updated = _doctor_out(doctor_id=did, specialty="Oncology")
        with patch(
            "domains.medai.services.doctor_service.DoctorService.update_doctor",
            new=AsyncMock(return_value=updated),
        ):
            resp = await async_client.patch(
                f"{BASE}/{did}",
                json={"specialty": "Oncology"},
                headers=admin_headers,
            )
        assert resp.status_code == 200
        assert resp.json()["data"]["specialty"] == "Oncology"

    async def test_update_unknown_doctor_returns_404(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        with patch(
            "domains.medai.services.doctor_service.DoctorService.update_doctor",
            new=AsyncMock(return_value=None),
        ):
            resp = await async_client.patch(
                f"{BASE}/{uuid.uuid4()}",
                json={"specialty": "X"},
                headers=admin_headers,
            )
        assert resp.status_code == 404

    async def test_update_requires_admin_role(
        self, async_client: AsyncClient, patient_headers: dict
    ):
        resp = await async_client.patch(
            f"{BASE}/{uuid.uuid4()}",
            json={"specialty": "X"},
            headers=patient_headers,
        )
        assert resp.status_code == 403


# ── Delete Doctor ─────────────────────────────────────────────────────────────

class TestDeleteDoctor:
    async def test_delete_doctor_returns_204(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        with patch(
            "domains.medai.services.doctor_service.DoctorService.delete_doctor",
            new=AsyncMock(return_value=True),
        ):
            resp = await async_client.delete(
                f"{BASE}/{uuid.uuid4()}", headers=admin_headers
            )
        assert resp.status_code == 204

    async def test_delete_unknown_doctor_returns_404(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        with patch(
            "domains.medai.services.doctor_service.DoctorService.delete_doctor",
            new=AsyncMock(return_value=False),
        ):
            resp = await async_client.delete(
                f"{BASE}/{uuid.uuid4()}", headers=admin_headers
            )
        assert resp.status_code == 404

    async def test_delete_requires_admin_role(
        self, async_client: AsyncClient, patient_headers: dict
    ):
        resp = await async_client.delete(
            f"{BASE}/{uuid.uuid4()}", headers=patient_headers
        )
        assert resp.status_code == 403
