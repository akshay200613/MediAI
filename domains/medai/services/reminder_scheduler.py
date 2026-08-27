"""
Appointment Reminder Scheduler – MedAI domain.

Runs a resilient background loop to send 30-minute pre-visit reminder emails
and track reminder status in the database.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config.logging import get_logger
from core.database.base import AsyncSessionLocal
from core.services.email_service import email_service
from domains.medai.models.appointment import Appointment, AppointmentStatus
from domains.medai.models.doctor import Doctor
from domains.medai.models.patient import Patient

logger = get_logger("medai.reminder_scheduler")


class AppointmentReminderScheduler:
    """
    Background worker that checks every interval for appointments occurring
    within the next 30-35 minutes and sends reminder emails.
    """

    def __init__(self, check_interval_seconds: int = 60) -> None:
        self.check_interval_seconds = check_interval_seconds
        self._task: asyncio.Task | None = None
        self._is_running = False

    def start(self) -> None:
        """Start the background scheduler task."""
        if self._is_running:
            return
        self._is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Appointment reminder background scheduler started", interval_sec=self.check_interval_seconds)

    async def stop(self) -> None:
        """Stop the background scheduler gracefully."""
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Appointment reminder background scheduler stopped")

    async def _run_loop(self) -> None:
        """Periodic background execution loop."""
        while self._is_running:
            try:
                await self.check_and_send_reminders()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error running reminder check loop", error=str(exc), exc_info=True)

            try:
                await asyncio.sleep(self.check_interval_seconds)
            except asyncio.CancelledError:
                break

    async def check_and_send_reminders(self, session: AsyncSession | None = None) -> int:
        """
        Scan database for upcoming appointments in the 30-minute reminder window
        and dispatch emails. Can be invoked directly or via background worker.
        """
        if session is not None:
            return await self._process_reminders_in_session(session)

        async with AsyncSessionLocal() as db_session:
            return await self._process_reminders_in_session(db_session)

    async def _process_reminders_in_session(self, session: AsyncSession) -> int:
        now = datetime.now(timezone.utc)
        # Reminder window: appointments starting between now and 35 minutes ahead
        # (allowing a 5-minute buffer so 30-min reminders are captured reliably)
        window_start = now - timedelta(minutes=5)
        window_end = now + timedelta(minutes=35)

        # Query qualifying appointments
        stmt = select(Appointment).where(
            Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
            Appointment.reminder_email_sent == False,  # noqa: E712
            Appointment.is_deleted == False,  # noqa: E712
            Appointment.scheduled_at >= window_start,
            Appointment.scheduled_at <= window_end,
        )

        res = await session.execute(stmt)
        appointments = res.scalars().all()

        reminders_sent = 0
        for appt in appointments:
            try:
                # 1. Resolve Patient
                pat_res = await session.execute(
                    select(Patient).where(Patient.id == uuid.UUID(str(appt.patient_id)), Patient.is_deleted == False)  # noqa: E712
                )
                patient = pat_res.scalar_one_or_none()
                if not patient:
                    # Fallback lookup by user_id
                    pat_res = await session.execute(
                        select(Patient).where(Patient.user_id == str(appt.patient_id), Patient.is_deleted == False)  # noqa: E712
                    )
                    patient = pat_res.scalar_one_or_none()

                # 2. Resolve Doctor
                doc_res = await session.execute(
                    select(Doctor).where(Doctor.id == uuid.UUID(str(appt.doctor_id)), Doctor.is_deleted == False)  # noqa: E712
                )
                doctor = doc_res.scalar_one_or_none()

                patient_email = patient.email if patient and patient.email else None
                patient_name = patient.full_name if patient else "Valued Patient"
                doc_name = doctor.full_name if doctor else "Doctor"
                doc_specialty = doctor.specialty if doctor else "General Practice"

                if patient_email:
                    subject, html_body = email_service.render_reminder_email(
                        patient_name=patient_name,
                        doctor_name=doc_name,
                        doctor_specialty=doc_specialty,
                        scheduled_at=appt.scheduled_at,
                        duration_minutes=appt.duration_minutes,
                        appointment_type=appt.appointment_type,
                    )
                    sent = await email_service.send_email(patient_email, subject, html_body)
                    if sent:
                        appt.reminder_email_sent = True
                        appt.reminder_sent_at = datetime.now(timezone.utc)
                        reminders_sent += 1
                        logger.info(
                            "30-minute reminder email sent",
                            recipient=patient_email,
                            appt_id=str(appt.id),
                            scheduled_at=str(appt.scheduled_at),
                        )
                else:
                    # If patient has no email on record, mark sent to prevent endless retries
                    appt.reminder_email_sent = True
                    appt.reminder_sent_at = datetime.now(timezone.utc)
                    logger.warning("Patient has no email on record; marked reminder as sent", appt_id=str(appt.id))

                await session.commit()

                # Optional: Broadcast real-time WebSocket reminder event
                try:
                    from domains.medai.websockets.manager import manager
                    await manager.notify_appointment_event(
                        "appointment_reminder_sent",
                        {"appointment_id": str(appt.id), "scheduled_at": appt.scheduled_at.isoformat()},
                        patient_id=str(appt.patient_id),
                        doctor_id=str(appt.doctor_id),
                    )
                except Exception:
                    pass

            except Exception as item_err:
                logger.error("Failed to process reminder for appointment", appt_id=str(appt.id), error=str(item_err))

        return reminders_sent


# Global reminder scheduler singleton
reminder_scheduler = AppointmentReminderScheduler()
