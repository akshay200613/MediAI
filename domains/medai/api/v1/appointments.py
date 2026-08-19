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


@router.post("/book", response_model=DataResponse[AppointmentOut], status_code=201, summary="Book appointment with double-booking prevention")
async def book_appointment(
    data: AppointmentCreate,
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_APPOINTMENT)),
) -> DataResponse[AppointmentOut]:
    """
    Book an appointment.
    Enforces no-double-booking rule at database query level.
    """
    from sqlalchemy import select
    from domains.medai.models.appointment import Appointment, AppointmentStatus

    # Double-booking check
    query = select(Appointment).where(
        Appointment.doctor_id == str(data.doctor_id),
        Appointment.scheduled_at == data.scheduled_at,
        Appointment.status != AppointmentStatus.CANCELLED,
        Appointment.is_deleted == False,
    )
    res = await session.execute(query)
    existing = res.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Double booking error: Doctor already has an active appointment at this selected time slot.",
        )

    svc = AppointmentService(session)
    appt = await svc.create_appointment(data)

    # Broadcast real-time WebSocket event
    from domains.medai.websockets.manager import manager
    try:
        await manager.notify_appointment_event(
            "appointment_created",
            appt.model_dump(mode="json"),
            patient_id=str(appt.patient_id),
            doctor_id=str(appt.doctor_id),
        )
    except Exception:
        pass

    return DataResponse(data=appt, message="Appointment booked successfully")


@router.get("", response_model=PaginatedResponse[AppointmentOut], summary="List appointments")
async def list_appointments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    upcoming_only: bool = Query(False),
    patient_id: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_APPOINTMENT)),
) -> PaginatedResponse[AppointmentOut]:
    svc = AppointmentService(session)

    # Patients can only see their own appointments — resolve patient record by auth user_id
    effective_patient_id = patient_id
    if current_user.role in ("patient", "user"):
        from domains.medai.services.patient_service import PatientService
        patient_svc = PatientService(session)
        patient_record = await patient_svc.get_patient_by_user_id(
            current_user.user_id, user_email=current_user.email
        )
        if patient_record:
            effective_patient_id = str(patient_record.id)
        else:
            # Patient user but no patient record yet — return empty list
            return PaginatedResponse(data=[], total=0, page=1, page_size=page_size, total_pages=0)

    if upcoming_only:
        appts = await svc.get_upcoming()
        if effective_patient_id:
            appts = [a for a in appts if str(a.patient_id) == effective_patient_id]
        return PaginatedResponse(data=appts, total=len(appts), page=1, page_size=len(appts), total_pages=1)
    if effective_patient_id:
        appts = await svc.get_by_patient(effective_patient_id)
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

    from domains.medai.websockets.manager import manager
    try:
        await manager.notify_appointment_event(
            "appointment_updated",
            appt.model_dump(mode="json"),
            patient_id=str(appt.patient_id),
            doctor_id=str(appt.doctor_id),
        )
    except Exception:
        pass

    return DataResponse(data=appt, message="Appointment updated")


@router.post("/{appt_id}/cancel", response_model=DataResponse[AppointmentOut], summary="Cancel appointment")
async def cancel_appointment(
    appt_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(Permission.UPDATE_APPOINTMENT)),
) -> DataResponse[AppointmentOut]:
    """
    Cancel an appointment.
    Patients can only cancel their own appointments.
    """
    from datetime import datetime, timedelta
    svc = AppointmentService(session)
    appt = await svc.get_appointment(appt_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Patients can only cancel their own appointments — check via patient record
    if getattr(current_user, "role", None) in ("patient", "user"):
        from domains.medai.services.patient_service import PatientService
        patient_svc = PatientService(session)
        patient_record = await patient_svc.get_patient_by_user_id(
            current_user.user_id, user_email=current_user.email
        )
        if not patient_record or str(appt.patient_id) != str(patient_record.id):
            raise HTTPException(status_code=403, detail="You can only cancel your own appointments")

    if appt.status in ("cancelled", "completed"):
        raise HTTPException(status_code=409, detail=f"Appointment is already {appt.status}")

    cancelled = await svc.cancel_appointment(appt_id)
    if not cancelled:
        raise HTTPException(status_code=500, detail="Failed to cancel appointment")

    from domains.medai.websockets.manager import manager
    try:
        await manager.notify_appointment_event(
            "appointment_cancelled",
            cancelled.model_dump(mode="json"),
            patient_id=str(cancelled.patient_id),
            doctor_id=str(cancelled.doctor_id),
        )
    except Exception:
        pass

    return DataResponse(data=cancelled, message="Appointment cancelled successfully")


@router.post("/{appt_id}/notes", response_model=DataResponse[dict], summary="Record consultation notes and ingest into RAG")
async def record_consultation_notes(
    appt_id: uuid.UUID,
    body: dict,
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(Permission.UPDATE_APPOINTMENT)),
) -> DataResponse[dict]:
    """
    Save consultation notes, mark appointment completed,
    and ingest notes into the RAG knowledge base for patient history tracking.
    """
    from core.ai.rag.pipeline import RAGPipeline
    from core.ai.llm.litellm_client import get_llm_client
    from domains.medai.models.appointment import Appointment, AppointmentStatus

    notes_text = body.get("notes", "").strip()
    prescription = body.get("prescription", "").strip()
    if not notes_text:
        raise HTTPException(status_code=400, detail="Consultation notes text is required")

    svc = AppointmentService(session)
    appt = await svc.get_appointment(appt_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    full_note = f"Consultation Notes: {notes_text}"
    if prescription:
        full_note += f"\nPrescription: {prescription}"

    # Update appointment status & notes
    appt.notes = full_note
    appt.status = AppointmentStatus.COMPLETED
    await session.commit()

    # Ingest into RAG pipeline
    try:
        pipeline = RAGPipeline(
            llm_client=get_llm_client(),
            collection_name="medai_knowledge",
        )
        source_id = str(uuid.uuid4())
        chunks_indexed = await pipeline.ingest(
            text=full_note,
            metadata={
                "title": f"Consultation Note - Patient {appt.patient_id[:8]}",
                "patient_id": str(appt.patient_id),
                "doctor_id": str(appt.doctor_id),
                "appointment_id": str(appt.id),
                "category": "consultation_notes",
            },
            source_id=source_id,
        )
    except Exception as e:
        chunks_indexed = 0

    return DataResponse(
        data={
            "appointment_id": str(appt.id),
            "status": appt.status,
            "chunks_indexed": chunks_indexed,
        },
        message="Consultation notes recorded and indexed into RAG pipeline",
    )
