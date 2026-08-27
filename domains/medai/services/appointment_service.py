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
        self.session = session
        self.repo = AppointmentRepository(session)

    async def create_appointment(self, data: AppointmentCreate) -> AppointmentOut:
        from sqlalchemy import select
        from domains.medai.models.appointment import Appointment, AppointmentStatus
        from domains.medai.models.doctor import Doctor
        from core.metrics import appointment_bookings_total
        import uuid

        # 1. Double-booking check
        query = select(Appointment).where(
            Appointment.doctor_id == str(data.doctor_id),
            Appointment.scheduled_at == data.scheduled_at,
            Appointment.status != AppointmentStatus.CANCELLED,
            Appointment.is_deleted == False,
        )
        res = await self.session.execute(query)
        existing = res.scalar_one_or_none()
        if existing:
            appointment_bookings_total.labels(outcome="conflict").inc()
            raise ValueError("Double booking error: Doctor already has an active appointment at this selected time slot.")

        # 2. Check doctor availability schedule strictly against doctor's profile
        doc_res = await self.session.execute(
            select(Doctor).where(Doctor.id == uuid.UUID(str(data.doctor_id)), Doctor.is_deleted == False)
        )
        doctor = doc_res.scalar_one_or_none()
        if doctor:
            if not doctor.is_available:
                raise ValueError(f"Doctor {doctor.full_name} is currently marked as unavailable.")

            # Validate doctor's available days
            all_days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
            day_map = {
                "monday": "mon", "mon": "mon",
                "tuesday": "tue", "tue": "tue",
                "wednesday": "wed", "wed": "wed",
                "thursday": "thu", "thu": "thu",
                "friday": "fri", "fri": "fri",
                "saturday": "sat", "sat": "sat",
                "sunday": "sun", "sun": "sun",
            }
            allowed_days = set()
            raw_days = (doctor.available_days or "Mon,Tue,Wed,Thu,Fri").lower().strip()
            if "-" in raw_days and "," not in raw_days:
                parts = raw_days.split("-")
                s_day = day_map.get(parts[0].strip(), "mon")
                e_day = day_map.get(parts[1].strip(), "fri")
                if s_day in all_days and e_day in all_days:
                    s_idx = all_days.index(s_day)
                    e_idx = all_days.index(e_day)
                    if s_idx <= e_idx:
                        allowed_days.update(all_days[s_idx:e_idx + 1])
                    else:
                        allowed_days.update(all_days[s_idx:] + all_days[:e_idx + 1])
            else:
                for token in raw_days.replace(";", ",").split(","):
                    token_clean = token.strip()
                    if token_clean in day_map:
                        allowed_days.add(day_map[token_clean])

            if not allowed_days:
                allowed_days = {"mon", "tue", "wed", "thu", "fri"}

            appt_day = data.scheduled_at.strftime("%a").lower()
            if appt_day not in allowed_days:
                day_display = data.scheduled_at.strftime("%A")
                raise ValueError(
                    f"Doctor {doctor.full_name} only accepts appointments on {doctor.available_days or 'Mon, Tue, Wed, Thu, Fri'}. "
                    f"Selected date is a {day_display}."
                )

            # Validate doctor's working hours
            def parse_time_mins(t_str: str | None, default_mins: int) -> int:
                if not t_str:
                    return default_mins
                try:
                    p = t_str.strip()[:5].split(":")
                    return int(p[0]) * 60 + (int(p[1]) if len(p) > 1 else 0)
                except Exception:
                    return default_mins

            start_mins = parse_time_mins(doctor.working_hours_start, 9 * 60)
            end_mins = parse_time_mins(doctor.working_hours_end, 17 * 60)

            appt_start_mins = data.scheduled_at.hour * 60 + data.scheduled_at.minute
            appt_end_mins = appt_start_mins + data.duration_minutes

            if appt_start_mins < start_mins or appt_end_mins > end_mins:
                slot_time = data.scheduled_at.strftime("%H:%M")
                start_str = f"{start_mins // 60:02d}:{start_mins % 60:02d}"
                end_str = f"{end_mins // 60:02d}:{end_mins % 60:02d}"
                raise ValueError(
                    f"Selected slot {slot_time} is outside Doctor {doctor.full_name}'s "
                    f"working hours ({start_str} - {end_str})."
                )

        appt = await self.repo.create({
            **data.model_dump(),
            "patient_id": str(data.patient_id),
            "doctor_id": str(data.doctor_id),
        })
        await self.session.commit()
        appointment_bookings_total.labels(outcome="success").inc()
        logger.info("Appointment created and committed to database", appt_id=str(appt.id))

        out = AppointmentOut.model_validate(appt)

        # Broadcast real-time WebSocket event
        try:
            from domains.medai.websockets.manager import manager
            await manager.notify_appointment_event(
                "appointment_created",
                out.model_dump(mode="json"),
                patient_id=str(out.patient_id),
                doctor_id=str(out.doctor_id),
            )
        except Exception as e:
            logger.warning(f"WebSocket notification failed: {e}")

        return out

    async def mark_past_uncompleted_appointments(self) -> int:
        """
        Auto-update scheduled/confirmed appointments whose scheduled time has passed
        and were not completed or cancelled, marking them as 'incomplete'.
        """
        from sqlalchemy import update
        from datetime import datetime, timezone
        from domains.medai.models.appointment import Appointment, AppointmentStatus

        now = datetime.now(timezone.utc)
        stmt = (
            update(Appointment)
            .where(
                Appointment.status.in_([
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.IN_PROGRESS
                ]),
                Appointment.scheduled_at < now,
                Appointment.is_deleted == False,
            )
            .values(status=AppointmentStatus.INCOMPLETE)
        )
        res = await self.session.execute(stmt)
        if res.rowcount > 0:
            await self.session.commit()
            logger.info("Marked past uncompleted appointments as incomplete", count=res.rowcount)
        return res.rowcount

    async def get_appointment(self, appt_id: uuid.UUID) -> AppointmentOut | None:
        await self.mark_past_uncompleted_appointments()
        appt = await self.repo.get_by_id(appt_id)
        return AppointmentOut.model_validate(appt) if appt else None

    async def list_appointments(self, page: int = 1, page_size: int = 20) -> PaginatedResponse[AppointmentOut]:
        await self.mark_past_uncompleted_appointments()
        offset = (page - 1) * page_size
        appts, total = await self.repo.list(offset=offset, limit=page_size, order_by="scheduled_at", descending=True)
        return PaginatedResponse(
            data=[AppointmentOut.model_validate(a) for a in appts],
            total=total, page=page, page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )

    async def update_appointment(self, appt_id: uuid.UUID, data: AppointmentUpdate) -> AppointmentOut | None:
        appt = await self.repo.update(appt_id, data.model_dump(exclude_none=True, exclude_unset=True))
        if not appt:
            return None
        await self.session.commit()
        return AppointmentOut.model_validate(appt)

    async def cancel_appointment(self, appt_id: uuid.UUID) -> AppointmentOut | None:
        appt = await self.repo.update(appt_id, {"status": "cancelled"})
        if not appt:
            return None
        await self.session.commit()
        out = AppointmentOut.model_validate(appt)
        try:
            from domains.medai.websockets.manager import manager
            await manager.notify_appointment_event(
                "appointment_cancelled",
                out.model_dump(mode="json"),
                patient_id=str(out.patient_id),
                doctor_id=str(out.doctor_id),
            )
        except Exception as e:
            logger.warning(f"WebSocket notification failed: {e}")
        return out

    async def get_upcoming(self) -> list[AppointmentOut]:
        await self.mark_past_uncompleted_appointments()
        appts = await self.repo.get_upcoming()
        return [AppointmentOut.model_validate(a) for a in appts]

    async def get_by_patient(self, patient_id: str) -> list[AppointmentOut]:
        await self.mark_past_uncompleted_appointments()
        appts = await self.repo.get_by_patient(patient_id)
        return [AppointmentOut.model_validate(a) for a in appts]


