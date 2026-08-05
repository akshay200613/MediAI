"""Doctor CRUD API – /api/v1/medai/doctors"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.session import get_db
from core.auth.dependencies import get_current_user, CurrentUser
from core.auth.permissions import require_permission, Permission
from core.schemas.base import DataResponse, PaginatedResponse
from domains.medai.schemas.doctor import DoctorCreate, DoctorOut, DoctorUpdate
from domains.medai.services.doctor_service import DoctorService

router = APIRouter()


@router.post("", response_model=DataResponse[DoctorOut], status_code=201, summary="Create doctor")
async def create_doctor(
    data: DoctorCreate,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
) -> DataResponse[DoctorOut]:
    svc = DoctorService(session)
    doctor = await svc.create_doctor(data)
    return DataResponse(data=doctor, message="Doctor created")


@router.get("", response_model=PaginatedResponse[DoctorOut], summary="List doctors")
async def list_doctors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    specialty: str | None = Query(None),
    available_only: bool = Query(False),
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> PaginatedResponse[DoctorOut]:
    svc = DoctorService(session)
    if search:
        doctors = await svc.search_doctors(search)
        return PaginatedResponse(data=doctors, total=len(doctors), page=1, page_size=len(doctors), total_pages=1)
    if available_only:
        doctors = await svc.get_available_doctors(specialty)
        return PaginatedResponse(data=doctors, total=len(doctors), page=1, page_size=len(doctors), total_pages=1)
    return await svc.list_doctors(page=page, page_size=page_size)


@router.get("/{doctor_id}", response_model=DataResponse[DoctorOut], summary="Get doctor")
async def get_doctor(
    doctor_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> DataResponse[DoctorOut]:
    svc = DoctorService(session)
    doctor = await svc.get_doctor(doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return DataResponse(data=doctor)


@router.patch("/{doctor_id}", response_model=DataResponse[DoctorOut], summary="Update doctor")
async def update_doctor(
    doctor_id: uuid.UUID,
    data: DoctorUpdate,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
) -> DataResponse[DoctorOut]:
    svc = DoctorService(session)
    doctor = await svc.update_doctor(doctor_id, data)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return DataResponse(data=doctor, message="Doctor updated")


@router.delete("/{doctor_id}", status_code=204, summary="Delete doctor")
async def delete_doctor(
    doctor_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
) -> None:
    svc = DoctorService(session)
    if not await svc.delete_doctor(doctor_id):
        raise HTTPException(status_code=404, detail="Doctor not found")
