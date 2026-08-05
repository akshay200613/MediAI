"""Doctor Repository."""
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from core.repositories.base_repository import BaseRepository
from domains.medai.models.doctor import Doctor


class DoctorRepository(BaseRepository[Doctor]):
    model = Doctor

    async def search(self, query: str, limit: int = 20) -> list[Doctor]:
        q = f"%{query.lower()}%"
        stmt = (
            select(Doctor)
            .where(
                Doctor.is_deleted == False,  # noqa: E712
                or_(
                    Doctor.first_name.ilike(q),
                    Doctor.last_name.ilike(q),
                    Doctor.specialty.ilike(q),
                    Doctor.email.ilike(q),
                ),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_available(self, specialty: str | None = None) -> list[Doctor]:
        stmt = select(Doctor).where(
            Doctor.is_deleted == False,  # noqa: E712
            Doctor.is_available == True,  # noqa: E712
        )
        if specialty:
            stmt = stmt.where(Doctor.specialty.ilike(f"%{specialty}%"))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
