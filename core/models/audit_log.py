"""
Audit Log model – tracks all significant actions across the platform.
"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base_model import BaseModel


class AuditLog(BaseModel):
    __tablename__ = "audit_logs"

    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    @property
    def entity_type(self) -> str:
        return self.resource_type

    @property
    def entity_id(self) -> str | None:
        return self.resource_id

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action} user={self.user_id}>"
