"""
Audit Log model – immutable record of all create/update/delete operations.
"""

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base_model import BaseModel


class AuditLog(BaseModel):
    __tablename__ = "audit_logs"

    # Who
    user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # What
    action: Mapped[str] = mapped_column(String(50), nullable=False)       # CREATE, UPDATE, DELETE, LOGIN
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)  # "Patient", "Appointment"
    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Context
    domain: Mapped[str] = mapped_column(String(50), nullable=False, default="platform")
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Payload (what changed)
    old_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<AuditLog action={self.action} entity={self.entity_type}/{self.entity_id}>"
