from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base_model import AuditableModel

if TYPE_CHECKING:
    from domains.medai.models.patient import Patient
    from domains.medai.models.doctor import Doctor


class User(AuditableModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
    domain: Mapped[str] = mapped_column(String(50), nullable=False, default="platform")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    patient: Mapped[Optional["Patient"]] = relationship("Patient", back_populates="user", uselist=False)
    doctor: Mapped[Optional["Doctor"]] = relationship("Doctor", back_populates="user", uselist=False)

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"

