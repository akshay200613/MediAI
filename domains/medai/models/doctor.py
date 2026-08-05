"""
Doctor model – MedAI domain.
"""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base_model import AuditableModel


class Doctor(AuditableModel):
    __tablename__ = "medai_doctors"

    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)

    # Professional
    specialty: Mapped[str] = mapped_column(String(100), nullable=False)
    license_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    years_of_experience: Mapped[int] = mapped_column(default=0, nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    consultation_fee: Mapped[float] = mapped_column(default=0.0, nullable=False)

    # Schedule
    available_days: Mapped[str | None] = mapped_column(String(100), nullable=True)  # JSON string
    working_hours_start: Mapped[str | None] = mapped_column(String(5), nullable=True)  # "09:00"
    working_hours_end: Mapped[str | None] = mapped_column(String(5), nullable=True)   # "17:00"
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def full_name(self) -> str:
        return f"Dr. {self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Doctor id={self.id} name={self.full_name} specialty={self.specialty}>"
