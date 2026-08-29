"""
Patient Repository – data access layer for patients.
"""

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.repositories.base_repository import BaseRepository
from domains.medai.models.patient import Patient


class PatientRepository(BaseRepository[Patient]):
    model = Patient

    async def get_by_user_id(self, user_id: str, user_email: str | None = None) -> Patient | None:
        """Fetch the patient record linked to an auth user with case-insensitive email fallback."""
        from sqlalchemy import func, or_
        conditions = [Patient.user_id == str(user_id)]
        if user_email:
            conditions.append(func.lower(Patient.email) == func.lower(user_email))
        stmt = (
            select(Patient)
            .where(
                Patient.is_deleted == False,
                or_(*conditions),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(self, query: str, limit: int = 20) -> list[Patient]:
        """Full-text search across name, phone, and email."""
        q = f"%{query.lower()}%"
        stmt = (
            select(Patient)
            .where(
                Patient.is_deleted == False,  # noqa: E712
                or_(
                    Patient.first_name.ilike(q),
                    Patient.last_name.ilike(q),
                    Patient.phone.ilike(q),
                    Patient.email.ilike(q),
                ),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
