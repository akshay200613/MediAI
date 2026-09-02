"""
Doctor Dashboard API – /api/v1/medai/doctor-dashboard
Endpoints exclusively for authenticated doctors to view their own data.
"""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_db
from core.auth.dependencies import CurrentUser
from core.auth.permissions import require_permission, Permission
from core.schemas.base import DataResponse
from domains.medai.models.appointment import Appointment
from domains.medai.models.doctor import Doctor
from domains.medai.models.patient import Patient

router = APIRouter()


def _require_doctor(current_user: CurrentUser) -> CurrentUser:
    if current_user.role not in ("doctor", "admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Doctor access required")
    return current_user


@router.get(
    "/today",
    response_model=DataResponse[dict],
    summary="Get today's appointments for the authenticated doctor",
)
async def get_today_appointments(
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_APPOINTMENT)),
) -> DataResponse[dict]:
    """
    Returns today's appointment count and list for the authenticated doctor.
    Joins with Patient table to resolve patient names.
    """
    # Resolve doctor record for this user
    doc_res = await session.execute(
        select(Doctor).where(
            Doctor.user_id == current_user.user_id,
            Doctor.is_deleted == False,
        )
    )
    doctor = doc_res.scalar_one_or_none()
    if not doctor:
        return DataResponse(
            data={"count": 0, "appointments": [], "doctor_name": ""},
            message="No doctor profile found",
        )

    # Today date range (UTC)
    now_utc = datetime.now(timezone.utc)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    appts_res = await session.execute(
        select(Appointment).where(
            and_(
                Appointment.doctor_id == str(doctor.id),
                Appointment.scheduled_at >= today_start,
                Appointment.scheduled_at < today_end,
                Appointment.is_deleted == False,
            )
        ).order_by(Appointment.scheduled_at)
    )
    appts = appts_res.scalars().all()

    # Resolve patient names
    appointment_list = []
    for a in appts:
        pat_res = await session.execute(
            select(Patient).where(Patient.id == a.patient_id, Patient.is_deleted == False)
        )
        patient = pat_res.scalar_one_or_none()
        appointment_list.append({
            "id": str(a.id),
            "patient_id": str(a.patient_id),
            "patient_name": patient.full_name if patient else f"Patient #{str(a.patient_id)[:8]}",
            "patient_phone": patient.phone if patient else None,
            "appointment_type": a.appointment_type,
            "status": a.status,
            "scheduled_at": a.scheduled_at.isoformat() if a.scheduled_at else None,
            "duration_minutes": a.duration_minutes,
            "reason": a.reason,
            "notes": a.notes,
        })

    return DataResponse(
        data={
            "count": len(appointment_list),
            "appointments": appointment_list,
            "doctor_name": doctor.full_name,
            "doctor_specialty": doctor.specialty,
            "profile_image_url": doctor.profile_image_url,
        },
        message="Today's appointments retrieved",
    )


@router.get(
    "/patients",
    response_model=DataResponse[list],
    summary="Get all patients the doctor has seen",
)
async def get_my_patients(
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_PATIENT)),
) -> DataResponse[list]:
    """
    Returns the list of unique patients the authenticated doctor has appointments with.
    """
    doc_res = await session.execute(
        select(Doctor).where(
            Doctor.user_id == current_user.user_id,
            Doctor.is_deleted == False,
        )
    )
    doctor = doc_res.scalar_one_or_none()
    if not doctor:
        return DataResponse(data=[], message="No doctor profile found")

    # Get distinct patient IDs from appointments
    appts_res = await session.execute(
        select(Appointment.patient_id).where(
            Appointment.doctor_id == str(doctor.id),
            Appointment.is_deleted == False,
        ).distinct()
    )
    patient_ids = [row[0] for row in appts_res.all()]

    patients_out = []
    for pid in patient_ids:
        pat_res = await session.execute(
            select(Patient).where(Patient.id == pid, Patient.is_deleted == False)
        )
        patient = pat_res.scalar_one_or_none()
        if not patient:
            continue

        # Count appointments with this doctor
        count = await session.scalar(
            select(func.count(Appointment.id)).where(
                Appointment.doctor_id == str(doctor.id),
                Appointment.patient_id == str(patient.id),
                Appointment.is_deleted == False,
            )
        )
        patients_out.append({
            "id": str(patient.id),
            "full_name": patient.full_name,
            "email": patient.email,
            "phone": patient.phone,
            "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            "gender": patient.gender,
            "blood_group": patient.blood_group,
            "allergies": patient.allergies,
            "chronic_conditions": patient.chronic_conditions,
            "appointment_count": count or 0,
        })

    return DataResponse(data=patients_out, message="Patient roster retrieved")


@router.get(
    "/patients/{patient_id}/history",
    response_model=DataResponse[dict],
    summary="Get a specific patient's medical history and appointment records",
)
async def get_patient_history(
    patient_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_PATIENT)),
) -> DataResponse[dict]:
    """
    Returns full patient profile plus their appointment history (with notes).
    """
    pat_res = await session.execute(
        select(Patient).where(Patient.id == patient_id, Patient.is_deleted == False)
    )
    patient = pat_res.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Appointment history for this patient
    appts_res = await session.execute(
        select(Appointment).where(
            Appointment.patient_id == patient_id,
            Appointment.is_deleted == False,
        ).order_by(Appointment.scheduled_at.desc())
    )
    appts = appts_res.scalars().all()

    history = [
        {
            "id": str(a.id),
            "doctor_id": str(a.doctor_id),
            "appointment_type": a.appointment_type,
            "status": a.status,
            "scheduled_at": a.scheduled_at.isoformat() if a.scheduled_at else None,
            "duration_minutes": a.duration_minutes,
            "reason": a.reason,
            "notes": a.notes,
            "ai_triage_summary": a.ai_triage_summary,
        }
        for a in appts
    ]

    return DataResponse(
        data={
            "patient": {
                "id": str(patient.id),
                "full_name": patient.full_name,
                "email": patient.email,
                "phone": patient.phone,
                "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                "gender": patient.gender,
                "blood_group": patient.blood_group,
                "address": patient.address,
                "city": patient.city,
                "state": patient.state,
                "allergies": patient.allergies,
                "chronic_conditions": patient.chronic_conditions,
                "emergency_contact_name": patient.emergency_contact_name,
                "emergency_contact_phone": patient.emergency_contact_phone,
            },
            "appointment_history": history,
        },
        message="Patient medical history retrieved",
    )
