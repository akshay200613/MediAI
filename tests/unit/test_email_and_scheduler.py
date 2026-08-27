"""
Unit tests for EmailService, Confirmation Emails, and Appointment Reminder Scheduler.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.services.email_service import EmailService, email_service
from domains.medai.models.appointment import Appointment, AppointmentStatus
from domains.medai.models.doctor import Doctor
from domains.medai.models.patient import Patient
from domains.medai.schemas.appointment import AppointmentCreate
from domains.medai.services.appointment_service import AppointmentService
from domains.medai.services.reminder_scheduler import AppointmentReminderScheduler


class TestEmailService:
    def test_render_confirmation_email(self) -> None:
        service = EmailService()
        now = datetime(2026, 9, 15, 10, 30, tzinfo=timezone.utc)
        subject, html = service.render_confirmation_email(
            patient_name="John Doe",
            doctor_name="Alice Smith",
            doctor_specialty="Cardiology",
            scheduled_at=now,
            duration_minutes=45,
            appointment_type="consultation",
            reason="Chest pain follow-up",
        )

        assert "Appointment Confirmed" in subject
        assert "Dr. Alice Smith" in subject
        assert "John Doe" in html
        assert "Cardiology" in html
        assert "45 Minutes" in html
        assert "Chest pain follow-up" in html

    def test_render_reminder_email(self) -> None:
        service = EmailService()
        now = datetime(2026, 9, 15, 11, 0, tzinfo=timezone.utc)
        subject, html = service.render_reminder_email(
            patient_name="Jane Doe",
            doctor_name="Bob Jones",
            doctor_specialty="Dermatology",
            scheduled_at=now,
            duration_minutes=30,
            appointment_type="consultation",
        )

        assert "Reminder" in subject
        assert "30 minutes" in subject
        assert "Dr. Bob Jones" in subject
        assert "Jane Doe" in html
        assert "Dermatology" in html

    async def test_send_email_simulated_when_unconfigured(self) -> None:
        service = EmailService()
        service.enabled = False

        res = await service.send_email("patient@example.com", "Test Subject", "<h1>Test</h1>")
        assert res is True

    async def test_send_email_invalid_recipient(self) -> None:
        service = EmailService()
        res = await service.send_email("invalid-email", "Test", "Content")
        assert res is False


class TestAppointmentConfirmationAndScheduler:
    async def test_create_appointment_dispatches_confirmation_email(self) -> None:
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        doctor_id = uuid.uuid4()
        patient_id = uuid.uuid4()

        # Mock Doctor
        mock_doctor = Doctor(
            id=doctor_id,
            first_name="Gregory",
            last_name="House",
            specialty="Diagnostic Medicine",
            is_available=True,
            available_days="Mon-Sun",
            working_hours_start="00:00",
            working_hours_end="23:59",
        )

        # Mock Patient
        mock_patient = Patient(
            id=patient_id,
            first_name="Arthur",
            last_name="Dent",
            email="arthur.dent@example.com",
            phone="555-0199",
        )

        # Mock Appointment object returned by repo
        now = datetime.now(timezone.utc) + timedelta(days=1)
        mock_appointment = Appointment(
            id=uuid.uuid4(),
            patient_id=str(patient_id),
            doctor_id=str(doctor_id),
            appointment_type="consultation",
            scheduled_at=now,
            status=AppointmentStatus.SCHEDULED,
            duration_minutes=30,
            reason="Routine checkup",
            confirmation_email_sent=False,
            reminder_email_sent=False,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )

        service = AppointmentService(mock_session)
        service.repo.create = AsyncMock(return_value=mock_appointment)

        # Configure session.execute to return doctor, no conflicting appointments, and patient
        mock_exec_result_empty = MagicMock()
        mock_exec_result_empty.scalar_one_or_none.return_value = None

        mock_exec_result_doctor = MagicMock()
        mock_exec_result_doctor.scalar_one_or_none.return_value = mock_doctor

        mock_exec_result_patient = MagicMock()
        mock_exec_result_patient.scalar_one_or_none.return_value = mock_patient

        # Responses sequence: 1. check conflict, 2. check doctor, 3. fetch patient for email
        mock_session.execute.side_effect = [
            mock_exec_result_empty,
            mock_exec_result_doctor,
            mock_exec_result_patient,
        ]

        with patch.object(email_service, "send_email", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            appt_create = AppointmentCreate(
                patient_id=patient_id,
                doctor_id=doctor_id,
                scheduled_at=now,
                appointment_type="consultation",
                reason="Routine checkup",
            )

            res = await service.create_appointment(appt_create)

            assert res.patient_id == patient_id
            assert mock_appointment.confirmation_email_sent is True
            mock_send.assert_awaited_once()

    async def test_scheduler_processes_30min_reminders(self) -> None:
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        doctor_id = uuid.uuid4()
        patient_id = uuid.uuid4()

        # Appointment occurring in 20 minutes (within the 30-35 min window)
        now = datetime.now(timezone.utc)
        scheduled_time = now + timedelta(minutes=20)
        mock_appt = Appointment(
            id=uuid.uuid4(),
            patient_id=str(patient_id),
            doctor_id=str(doctor_id),
            appointment_type="consultation",
            scheduled_at=scheduled_time,
            status=AppointmentStatus.SCHEDULED,
            duration_minutes=30,
            reason="Checkup",
            reminder_email_sent=False,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )

        mock_doctor = Doctor(
            id=doctor_id,
            first_name="Stephen",
            last_name="Strange",
            specialty="Neurology",
        )

        mock_patient = Patient(
            id=patient_id,
            first_name="Wanda",
            last_name="Maximoff",
            email="wanda@example.com",
            phone="555-0123",
        )

        mock_appts_res = MagicMock()
        mock_appts_res.scalars.return_value.all.return_value = [mock_appt]

        mock_pat_res = MagicMock()
        mock_pat_res.scalar_one_or_none.return_value = mock_patient

        mock_doc_res = MagicMock()
        mock_doc_res.scalar_one_or_none.return_value = mock_doctor

        # 1. Query appointments, 2. Patient lookup, 3. Doctor lookup
        mock_session.execute.side_effect = [
            mock_appts_res,
            mock_pat_res,
            mock_doc_res,
        ]

        scheduler = AppointmentReminderScheduler(check_interval_seconds=10)

        with patch.object(email_service, "send_email", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            sent_count = await scheduler.check_and_send_reminders(session=mock_session)

            assert sent_count == 1
            assert mock_appt.reminder_email_sent is True
            assert mock_appt.reminder_sent_at is not None
            mock_send.assert_awaited_once()
