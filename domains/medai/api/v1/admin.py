"""
Admin API Endpoints – /api/v1/medai/admin
Handles doctor approvals, audit log viewing, and system analytics.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_db
from core.auth.dependencies import CurrentUser
from core.auth.permissions import require_permission, Permission
from core.schemas.base import DataResponse
from core.models.user import User
from core.models.audit_log import AuditLog
from domains.medai.models.doctor import Doctor
from domains.medai.models.patient import Patient
from domains.medai.models.appointment import Appointment

router = APIRouter()


@router.get(
    "/stats",
    response_model=DataResponse[dict],
    summary="Get system-wide admin analytics",
    dependencies=[Depends(require_permission(Permission.MANAGE_USERS))],
)
async def get_admin_stats(
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Retrieve system analytics, total counts, and per-doctor appointment breakdown."""
    # Count totals
    total_doctors = await session.scalar(select(func.count(Doctor.id)).where(Doctor.is_deleted == False))
    total_patients = await session.scalar(select(func.count(Patient.id)).where(Patient.is_deleted == False))
    total_appointments = await session.scalar(select(func.count(Appointment.id)).where(Appointment.is_deleted == False))
    
    # Accurate count of unverified pending doctors
    pending_doctors = await session.scalar(
        select(func.count(Doctor.id))
        .select_from(Doctor)
        .join(User, Doctor.email == User.email)
        .where(
            User.is_verified == False,
            User.is_deleted == False,
            Doctor.is_deleted == False,
        )
    )

    # Per-doctor breakdown
    doctor_query = select(Doctor).where(Doctor.is_deleted == False)
    doc_res = await session.execute(doctor_query)
    doctors = doc_res.scalars().all()

    doctor_breakdown = []
    for d in doctors:
        appt_count = await session.scalar(
            select(func.count(Appointment.id)).where(
                Appointment.doctor_id == str(d.id), Appointment.is_deleted == False
            )
        )
        doctor_breakdown.append({
            "doctor_id": str(d.id),
            "doctor_name": d.full_name,
            "specialty": d.specialty,
            "appointment_count": appt_count or 0,
            "is_available": d.is_available,
        })

    return DataResponse(
        data={
            "total_doctors": total_doctors or 0,
            "total_patients": total_patients or 0,
            "total_appointments": total_appointments or 0,
            "pending_doctor_approvals": pending_doctors or 0,
            "doctor_breakdown": doctor_breakdown,
        },
        message="Admin analytics retrieved",
    )


@router.get(
    "/doctors/pending",
    response_model=DataResponse[list[dict]],
    summary="List pending doctor approvals",
    dependencies=[Depends(require_permission(Permission.MANAGE_USERS))],
)
async def list_pending_doctors(
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[dict]]:
    """List doctor user accounts awaiting admin verification."""
    query = (
        select(Doctor, User)
        .select_from(Doctor)
        .join(User, Doctor.email == User.email)
        .where(
            User.is_verified == False,
            User.is_deleted == False,
            Doctor.is_deleted == False,
        )
    )
    res = await session.execute(query)
    rows = res.all()

    pending_list = []
    for doc, user in rows:
        pending_list.append({
            "doctor_id": str(doc.id),
            "user_id": str(user.id),
            "full_name": doc.full_name,
            "email": doc.email,
            "phone": doc.phone,
            "specialty": doc.specialty,
            "license_number": doc.license_number,
            "years_of_experience": doc.years_of_experience,
            "bio": doc.bio,
            "consultation_fee": doc.consultation_fee,
            "available_days": doc.available_days,
            "working_hours_start": doc.working_hours_start,
            "working_hours_end": doc.working_hours_end,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        })

    return DataResponse(data=pending_list, message="Pending doctors retrieved")


@router.post(
    "/doctors/{doctor_id}/approve",
    response_model=DataResponse[dict],
    summary="Approve a pending doctor signup",
    dependencies=[Depends(require_permission(Permission.MANAGE_USERS))],
)
async def approve_doctor(
    doctor_id: str,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Approve doctor registration: set User role='doctor', is_verified=True, Doctor is_available=True."""
    doc_res = await session.execute(select(Doctor).where(Doctor.id == doctor_id))
    doc = doc_res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor not found")

    user_res = await session.execute(select(User).where(User.email == doc.email))
    user = user_res.scalar_one_or_none()
    if user:
        user.role = "doctor"
        user.is_verified = True

    doc.is_available = True
    await session.commit()

    return DataResponse(
        data={"doctor_id": str(doc.id), "status": "approved"},
        message=f"Doctor {doc.full_name} approved successfully",
    )


@router.delete(
    "/doctors/{doctor_id}",
    response_model=DataResponse[dict],
    summary="Delete a doctor account and linked user",
    dependencies=[Depends(require_permission(Permission.MANAGE_USERS))],
)
async def delete_doctor_admin(
    doctor_id: str,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Soft-delete a doctor record and deactivate their linked user account."""
    doc_res = await session.execute(select(Doctor).where(Doctor.id == doctor_id))
    doc = doc_res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor not found")

    doc.is_deleted = True
    doc.is_available = False

    user_res = await session.execute(select(User).where(User.email == doc.email))
    user = user_res.scalar_one_or_none()
    if user:
        user.is_active = False
        user.is_deleted = True

    await session.commit()

    return DataResponse(
        data={"doctor_id": str(doc.id), "status": "deleted"},
        message=f"Doctor {doc.full_name} deleted successfully",
    )




@router.get(
    "/audit-logs",
    response_model=DataResponse[list[dict]],
    summary="View system audit logs",
    dependencies=[Depends(require_permission(Permission.VIEW_AUDIT_LOGS))],
)
async def get_audit_logs(
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[dict]]:
    """Retrieve audit trail of recent platform actions."""
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    res = await session.execute(query)
    logs = res.scalars().all()

    items = [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id) if log.entity_id else None,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
    return DataResponse(data=items, message="Audit logs retrieved")
