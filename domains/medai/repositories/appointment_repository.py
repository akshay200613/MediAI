"""Appointment Repository."""
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from core.repositories.base_repository import BaseRepository
from domains.medai.models.appointment import Appointment


class AppointmentRepository(BaseRepository[Appointment]):
    model = Appointment

    async def get_by_patient(self, patient_id: str) -> list[Appointment]:
        stmt = (
            select(Appointment)
            .where(Appointment.patient_id == patient_id, Appointment.is_deleted == False)  # noqa: E712
            .order_by(Appointment.scheduled_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_doctor(self, doctor_id: str) -> list[Appointment]:
        stmt = (
            select(Appointment)
            .where(Appointment.doctor_id == doctor_id, Appointment.is_deleted == False)  # noqa: E712
            .order_by(Appointment.scheduled_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_upcoming(self, limit: int = 20) -> list[Appointment]:
        now = datetime.utcnow()
        stmt = (
            select(Appointment)
            .where(
                Appointment.is_deleted == False,  # noqa: E712
                Appointment.scheduled_at >= now,
                Appointment.status.in_(["scheduled", "confirmed"]),
            )
            .order_by(Appointment.scheduled_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
