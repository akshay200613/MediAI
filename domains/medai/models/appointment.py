"""
Appointment model – MedAI domain.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base_model import AuditableModel


class AppointmentStatus(StrEnum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class AppointmentType(StrEnum):
    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    EMERGENCY = "emergency"
    LAB_TEST = "lab_test"
    VACCINATION = "vaccination"


class Appointment(AuditableModel):
    __tablename__ = "medai_appointments"

    patient_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    doctor_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)

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

    def __repr__(self) -> str:
        return f"<Appointment id={self.id} status={self.status} at={self.scheduled_at}>"
