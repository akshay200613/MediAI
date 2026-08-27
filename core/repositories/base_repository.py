"""
Generic Base Repository – async SQLAlchemy CRUD operations.
All domain repositories inherit from this class.
"""

from typing import Any, Generic, Type, TypeVar
from uuid import UUID

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic async repository providing standard CRUD operations.

    Usage:
        class PatientRepository(BaseRepository[Patient]):
            model = Patient
    """

    model: Type[ModelType]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id: UUID) -> ModelType | None:
        """Fetch a single record by primary key."""
        result = await self.session.get(self.model, id)
        return result

    async def get_by_field(self, field: str, value: Any) -> ModelType | None:
        """Fetch a single record matching a field value."""
        stmt = select(self.model).where(getattr(self.model, field) == value)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        offset: int = 0,
        limit: int = 20,
        order_by: str = "created_at",
        descending: bool = True,
    ) -> tuple[list[ModelType], int]:
        """
        Paginated list with optional filters.
        Returns (items, total_count).
        """
        stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)

        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    stmt = stmt.where(getattr(self.model, field) == value)
                    count_stmt = count_stmt.where(getattr(self.model, field) == value)

        # Soft delete filter
        if hasattr(self.model, "is_deleted"):
            stmt = stmt.where(self.model.is_deleted == False)  # noqa: E712
            count_stmt = count_stmt.where(self.model.is_deleted == False)  # noqa: E712

        # Order
        order_col = getattr(self.model, order_by, None)
        if order_col is not None:
            stmt = stmt.order_by(order_col.desc() if descending else order_col.asc())

        # Pagination
        stmt = stmt.offset(offset).limit(limit)

        import asyncio

        items_result, count_result = await asyncio.gather(
            self.session.execute(stmt),
            self.session.execute(count_stmt)
        )

        return list(items_result.scalars().all()), count_result.scalar_one()

    async def create(self, data: dict[str, Any]) -> ModelType:
        """Create and persist a new record."""
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: UUID, data: dict[str, Any]) -> ModelType | None:
        """Update a record by ID. Returns updated instance or None."""
        instance = await self.get_by_id(id)
        if instance is None:
            return None
        for field, value in data.items():
            if hasattr(instance, field):
                setattr(instance, field, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id: UUID) -> bool:
        """Hard delete a record by ID."""
        instance = await self.get_by_id(id)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def soft_delete(self, id: UUID) -> bool:
        """Soft delete – sets is_deleted=True and deleted_at=now()."""
        from datetime import datetime, timezone
        instance = await self.get_by_id(id)
        if instance is None or not hasattr(instance, "is_deleted"):
            return False
        instance.is_deleted = True  # type: ignore
        instance.deleted_at = datetime.now(timezone.utc)  # type: ignore
        await self.session.flush()
        return True

    async def exists(self, field: str, value: Any) -> bool:
        """Check if a record with the given field value exists."""
        stmt = select(func.count()).select_from(self.model).where(
            getattr(self.model, field) == value
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0
