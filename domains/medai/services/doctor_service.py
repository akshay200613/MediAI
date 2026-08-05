"""Doctor Service – business logic."""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from core.schemas.base import PaginatedResponse
from domains.medai.models.doctor import Doctor
from domains.medai.repositories.doctor_repository import DoctorRepository
from domains.medai.schemas.doctor import DoctorCreate, DoctorOut, DoctorUpdate
from core.config.logging import get_logger

logger = get_logger("medai.doctor_service")


class DoctorService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = DoctorRepository(session)

    async def create_doctor(self, data: DoctorCreate) -> DoctorOut:
        # Use a placeholder user_id — in production link to real User
        payload = data.model_dump(exclude_none=True)
        payload["user_id"] = str(uuid.uuid4())
        doctor = await self.repo.create(payload)
        logger.info("Doctor created", doctor_id=str(doctor.id))
        return self._to_out(doctor)

    async def get_doctor(self, doctor_id: uuid.UUID) -> DoctorOut | None:
        doctor = await self.repo.get_by_id(doctor_id)
        return self._to_out(doctor) if doctor else None

    async def list_doctors(self, page: int = 1, page_size: int = 20) -> PaginatedResponse[DoctorOut]:
        offset = (page - 1) * page_size
        doctors, total = await self.repo.list(offset=offset, limit=page_size)
        return PaginatedResponse(
            data=[self._to_out(d) for d in doctors],
            total=total, page=page, page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )

    async def update_doctor(self, doctor_id: uuid.UUID, data: DoctorUpdate) -> DoctorOut | None:
        doctor = await self.repo.update(doctor_id, data.model_dump(exclude_none=True, exclude_unset=True))
        return self._to_out(doctor) if doctor else None

    async def delete_doctor(self, doctor_id: uuid.UUID) -> bool:
        return await self.repo.soft_delete(doctor_id)

    async def search_doctors(self, query: str) -> list[DoctorOut]:
        doctors = await self.repo.search(query)
        return [self._to_out(d) for d in doctors]

    async def get_available_doctors(self, specialty: str | None = None) -> list[DoctorOut]:
        doctors = await self.repo.get_available(specialty)
        return [self._to_out(d) for d in doctors]

    @staticmethod
    def _to_out(doctor: Doctor) -> DoctorOut:
        data = DoctorOut.model_validate(doctor)
        data.full_name = doctor.full_name
        return data
