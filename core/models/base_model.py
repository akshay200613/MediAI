"""
Base SQLAlchemy model with reusable mixins.
All domain models should inherit from these mixins.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base


class UUIDMixin:
    """Adds a UUID primary key."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )


class TimestampMixin:
    """Adds created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Adds soft delete support (is_deleted flag + deleted_at timestamp)."""
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """
    Abstract base for all models.
    Inherit from this for standard CRUD entities.
    """
    __abstract__ = True


class AuditableModel(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Abstract base for models that need soft delete + audit trail.
    """
    __abstract__ = True
