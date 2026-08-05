"""Appointment Service – business logic."""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from core.schemas.base import PaginatedResponse
from domains.medai.models.appointment import Appointment
from domains.medai.repositories.appointment_repository import AppointmentRepository
from domains.medai.schemas.appointment import AppointmentCreate, AppointmentOut, AppointmentUpdate
from core.config.logging import get_logger

logger = get_logger("medai.appointment_service")


class AppointmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = AppointmentRepository(session)

    async def create_appointment(self, data: AppointmentCreate) -> AppointmentOut:
        appt = await self.repo.create({
            **data.model_dump(),
            "patient_id": str(data.patient_id),
            "doctor_id": str(data.doctor_id),
        })
        logger.info("Appointment created", appt_id=str(appt.id))
        return AppointmentOut.model_validate(appt)

    async def get_appointment(self, appt_id: uuid.UUID) -> AppointmentOut | None:
        appt = await self.repo.get_by_id(appt_id)
        return AppointmentOut.model_validate(appt) if appt else None

    async def list_appointments(self, page: int = 1, page_size: int = 20) -> PaginatedResponse[AppointmentOut]:
        offset = (page - 1) * page_size
        appts, total = await self.repo.list(offset=offset, limit=page_size, order_by="scheduled_at", descending=False)
        return PaginatedResponse(
            data=[AppointmentOut.model_validate(a) for a in appts],
            total=total, page=page, page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )

    async def update_appointment(self, appt_id: uuid.UUID, data: AppointmentUpdate) -> AppointmentOut | None:
        appt = await self.repo.update(appt_id, data.model_dump(exclude_none=True, exclude_unset=True))
        return AppointmentOut.model_validate(appt) if appt else None

    async def cancel_appointment(self, appt_id: uuid.UUID) -> AppointmentOut | None:
        appt = await self.repo.update(appt_id, {"status": "cancelled"})
        return AppointmentOut.model_validate(appt) if appt else None

    async def get_upcoming(self) -> list[AppointmentOut]:
        appts = await self.repo.get_upcoming()
        return [AppointmentOut.model_validate(a) for a in appts]

    async def get_by_patient(self, patient_id: str) -> list[AppointmentOut]:
        appts = await self.repo.get_by_patient(patient_id)
        return [AppointmentOut.model_validate(a) for a in appts]
