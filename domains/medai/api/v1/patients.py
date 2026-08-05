"""
Patient CRUD API Endpoints – /api/v1/medai/patients
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_db
from core.auth.dependencies import get_current_user, CurrentUser
from core.auth.permissions import require_permission, Permission
from core.schemas.base import DataResponse, PaginatedResponse
from domains.medai.schemas.patient import PatientCreate, PatientOut, PatientUpdate
from domains.medai.services.patient_service import PatientService

router = APIRouter()


@router.post(
    "",
    response_model=DataResponse[PatientOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new patient",
)
async def create_patient(
    data: PatientCreate,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission(Permission.CREATE_PATIENT)),
) -> DataResponse[PatientOut]:
    svc = PatientService(session)
    patient = await svc.create_patient(data)
    return DataResponse(data=patient, message="Patient created successfully")


@router.get(
    "",
    response_model=PaginatedResponse[PatientOut],
    summary="List all patients",
)
async def list_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission(Permission.VIEW_PATIENT)),
) -> PaginatedResponse[PatientOut]:
    svc = PatientService(session)
    if search:
        patients = await svc.search_patients(search)
        return PaginatedResponse(
            data=patients, total=len(patients), page=1,
            page_size=len(patients), total_pages=1,
        )
    return await svc.list_patients(page=page, page_size=page_size)


@router.get(
    "/{patient_id}",
    response_model=DataResponse[PatientOut],
    summary="Get patient by ID",
)
async def get_patient(
    patient_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission(Permission.VIEW_PATIENT)),
) -> DataResponse[PatientOut]:
    svc = PatientService(session)
    patient = await svc.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return DataResponse(data=patient)


@router.patch(
    "/{patient_id}",
    response_model=DataResponse[PatientOut],
    summary="Update patient",
)
async def update_patient(
    patient_id: uuid.UUID,
    data: PatientUpdate,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission(Permission.UPDATE_PATIENT)),
) -> DataResponse[PatientOut]:
    svc = PatientService(session)
    patient = await svc.update_patient(patient_id, data)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return DataResponse(data=patient, message="Patient updated")


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete patient (soft)",
)
async def delete_patient(
    patient_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission(Permission.DELETE_PATIENT)),
) -> None:
    svc = PatientService(session)
    deleted = await svc.delete_patient(patient_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Patient not found")
