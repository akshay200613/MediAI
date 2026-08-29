"""
Appointment model – MedAI domain.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base_model import AuditableModel

if TYPE_CHECKING:
    from domains.medai.models.patient import Patient
    from domains.medai.models.doctor import Doctor


class AppointmentStatus(StrEnum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    INCOMPLETE = "incomplete"


class AppointmentType(StrEnum):
    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    EMERGENCY = "emergency"
    LAB_TEST = "lab_test"
    VACCINATION = "vaccination"


class Appointment(AuditableModel):
    __tablename__ = "medai_appointments"
    __table_args__ = (
        Index("ix_medai_appointments_doctor_scheduled", "doctor_id", "scheduled_at", "status"),
        Index("ix_medai_appointments_patient_status", "patient_id", "status"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("medai_patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("medai_doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    appointment_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default=AppointmentType.CONSULTATION
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=AppointmentStatus.SCHEDULED, index=True
    )

    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(default=30, nullable=False)

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_triage_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Email notifications & reminder tracking
    confirmation_email_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reminder_email_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="appointments", foreign_keys=[patient_id])
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="appointments", foreign_keys=[doctor_id])

    def __repr__(self) -> str:
        return f"<Appointment id={self.id} status={self.status} at={self.scheduled_at}>"

