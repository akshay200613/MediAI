"""Appointment CRUD API – /api/v1/medai/appointments"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.session import get_db
from core.auth.dependencies import get_current_user, CurrentUser
from core.auth.permissions import require_permission, Permission
from core.schemas.base import DataResponse, PaginatedResponse
from domains.medai.schemas.appointment import AppointmentCreate, AppointmentOut, AppointmentUpdate
from domains.medai.services.appointment_service import AppointmentService

router = APIRouter()


@router.post("", response_model=DataResponse[AppointmentOut], status_code=201, summary="Create appointment")
async def create_appointment(
    data: AppointmentCreate,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission(Permission.CREATE_APPOINTMENT)),
) -> DataResponse[AppointmentOut]:
    svc = AppointmentService(session)
    appt = await svc.create_appointment(data)
    return DataResponse(data=appt, message="Appointment created")


@router.get("", response_model=PaginatedResponse[AppointmentOut], summary="List appointments")
async def list_appointments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    upcoming_only: bool = Query(False),
    patient_id: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission(Permission.VIEW_APPOINTMENT)),
) -> PaginatedResponse[AppointmentOut]:
    svc = AppointmentService(session)
    if upcoming_only:
        appts = await svc.get_upcoming()
        return PaginatedResponse(data=appts, total=len(appts), page=1, page_size=len(appts), total_pages=1)
    if patient_id:
        appts = await svc.get_by_patient(patient_id)
        return PaginatedResponse(data=appts, total=len(appts), page=1, page_size=len(appts), total_pages=1)
    return await svc.list_appointments(page=page, page_size=page_size)


@router.get("/{appt_id}", response_model=DataResponse[AppointmentOut], summary="Get appointment")
async def get_appointment(
    appt_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission(Permission.VIEW_APPOINTMENT)),
) -> DataResponse[AppointmentOut]:
    svc = AppointmentService(session)
    appt = await svc.get_appointment(appt_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return DataResponse(data=appt)


@router.patch("/{appt_id}", response_model=DataResponse[AppointmentOut], summary="Update appointment")
async def update_appointment(
    appt_id: uuid.UUID,
    data: AppointmentUpdate,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission(Permission.UPDATE_APPOINTMENT)),
) -> DataResponse[AppointmentOut]:
    svc = AppointmentService(session)
    appt = await svc.update_appointment(appt_id, data)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return DataResponse(data=appt, message="Appointment updated")


@router.post("/{appt_id}/cancel", response_model=DataResponse[AppointmentOut], summary="Cancel appointment")
async def cancel_appointment(
    appt_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission(Permission.UPDATE_APPOINTMENT)),
) -> DataResponse[AppointmentOut]:
    svc = AppointmentService(session)
    appt = await svc.cancel_appointment(appt_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return DataResponse(data=appt, message="Appointment cancelled")
