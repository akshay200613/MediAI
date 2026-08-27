"""
Patient Service – business logic for patient management.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas.base import PaginatedResponse
from domains.medai.models.patient import Patient
from domains.medai.repositories.patient_repository import PatientRepository
from domains.medai.schemas.patient import PatientCreate, PatientOut, PatientUpdate
from core.config.logging import get_logger

logger = get_logger("medai.patient_service")


class PatientService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PatientRepository(session)

    async def create_patient(self, data: PatientCreate) -> PatientOut:
        patient = await self.repo.create(data.model_dump(exclude_none=True))
        await self.session.commit()
        logger.info("Patient created", patient_id=str(patient.id))
        return self._to_out(patient)

    async def get_patient(self, patient_id: uuid.UUID) -> PatientOut | None:
        patient = await self.repo.get_by_id(patient_id)
        return self._to_out(patient) if patient else None

    async def get_patient_by_user_id(self, user_id: str, user_email: str | None = None) -> PatientOut | None:
        """
        Resolve the patient record from an auth user's UUID.
        Falls back to email lookup for existing patients where user_id was not set.
        """
        patient = await self.repo.get_by_user_id(user_id)
        if patient:
            # Backfill user_id if missing (migration support)
            return self._to_out(patient)
        # Fallback: look up by email for pre-existing patients
        if user_email:
            patient = await self.repo.get_by_field("email", user_email)
            if patient and not patient.is_deleted:
                return self._to_out(patient)
        return None


    async def list_patients(
        self, page: int = 1, page_size: int = 20
    ) -> PaginatedResponse[PatientOut]:
        offset = (page - 1) * page_size
        patients, total = await self.repo.list(offset=offset, limit=page_size)
        total_pages = (total + page_size - 1) // page_size

        return PaginatedResponse(
            data=[self._to_out(p) for p in patients],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def update_patient(
        self, patient_id: uuid.UUID, data: PatientUpdate
    ) -> PatientOut | None:
        patient = await self.repo.update(
            patient_id, data.model_dump(exclude_none=True, exclude_unset=True)
        )
        if not patient:
            return None
        await self.session.commit()
        return self._to_out(patient)

    async def delete_patient(self, patient_id: uuid.UUID) -> bool:
        res = await self.repo.soft_delete(patient_id)
        if res:
            await self.session.commit()
        return res

    async def search_patients(self, query: str) -> list[PatientOut]:
        patients = await self.repo.search(query)
        return [self._to_out(p) for p in patients]

    @staticmethod
    def _to_out(patient: Patient) -> PatientOut:
        data = PatientOut.model_validate(patient)
        data.full_name = patient.full_name
        return data
