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


@router.get(
    "/me/profile-status",
    summary="Get current patient profile completeness status",
)
async def get_my_profile_status(
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    svc = PatientService(session)
    patient = await svc.get_patient_by_user_id(current_user.user_id, user_email=current_user.email)
    completeness = PatientService.check_profile_completeness(patient)
    return DataResponse(
        data={
            "patient": patient,
            "is_complete": completeness["is_complete"],
            "missing_fields": completeness["missing_fields"],
            "message": completeness["message"],
        }
    )


@router.patch(
    "/me",
    response_model=DataResponse[PatientOut],
    summary="Update current patient's own profile",
)
async def update_my_profile(
    data: PatientUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> DataResponse[PatientOut]:
    svc = PatientService(session)
    patient = await svc.get_patient_by_user_id(current_user.user_id, user_email=current_user.email)
    if not patient:
        # Create initial patient record for logged in user
        names = (current_user.full_name or "Patient User").split(" ", 1)
        first_name = data.first_name or (names[0] if names[0] else "Patient")
        last_name = data.last_name or (names[1] if len(names) > 1 and names[1].strip() else "User")
        patient = await svc.create_patient(
            PatientCreate(
                first_name=first_name,
                last_name=last_name,
                email=current_user.email,
                phone=data.phone or "000-000-0000",
                date_of_birth=data.date_of_birth,
                gender=data.gender,
                blood_group=data.blood_group,
                address=data.address,
                city=data.city,
                allergies=data.allergies,
                chronic_conditions=data.chronic_conditions,
                user_id=current_user.user_id,
            )
        )
        return DataResponse(data=patient, message="Medical profile created successfully")

    updated = await svc.update_patient(patient.id, data)
    return DataResponse(data=updated, message="Medical profile updated successfully")


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
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_PATIENT)),
) -> PaginatedResponse[PatientOut]:
    if current_user.role in ("patient", "user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Patients are not permitted to list the patient registry",
        )

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
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_PATIENT)),
) -> DataResponse[PatientOut]:
    svc = PatientService(session)

    # Authorization / BOLA check
    if current_user.role in ("patient", "user"):
        pat_record = await svc.get_patient_by_user_id(current_user.user_id, user_email=current_user.email)
        valid_ids = {str(current_user.user_id)}
        if pat_record:
            valid_ids.add(str(pat_record.id))
        if str(patient_id) not in valid_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only view your own patient record",
            )

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
    current_user: CurrentUser = Depends(require_permission(Permission.UPDATE_PATIENT)),
) -> DataResponse[PatientOut]:
    svc = PatientService(session)

    # Authorization / BOLA check
    if current_user.role in ("patient", "user"):
        pat_record = await svc.get_patient_by_user_id(current_user.user_id, user_email=current_user.email)
        valid_ids = {str(current_user.user_id)}
        if pat_record:
            valid_ids.add(str(pat_record.id))
        if str(patient_id) not in valid_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only update your own patient record",
            )

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
    current_user: CurrentUser = Depends(require_permission(Permission.DELETE_PATIENT)),
) -> None:
    if current_user.role in ("patient", "user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Patients cannot delete patient records",
        )

    svc = PatientService(session)
    deleted = await svc.delete_patient(patient_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Patient not found")
