"""
Admin API Endpoints – /api/v1/medai/admin
Handles doctor approvals, audit log viewing, and system analytics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
)
async def approve_doctor(
    doctor_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
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

    # Log approval to Audit Trail
    try:
        from core.services.audit_service import log_audit_event
        await log_audit_event(
            session=session,
            user_id=str(current_user.user_id),
            user_name=current_user.full_name,
            user_role=current_user.role,
            action="DOCTOR_APPROVED",
            resource_type="Doctor",
            resource_id=str(doc.id),
            details={"doctor_name": doc.full_name, "specialty": doc.specialty, "email": doc.email},
        )
    except Exception:
        pass

    await session.commit()

    return DataResponse(
        data={"doctor_id": str(doc.id), "status": "approved"},
        message=f"Doctor {doc.full_name} approved successfully",
    )


@router.delete(
    "/doctors/{doctor_id}",
    response_model=DataResponse[dict],
    summary="Delete a doctor account and linked user",
)
async def delete_doctor_admin(
    doctor_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
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

    # Log deletion to Audit Trail
    try:
        from core.services.audit_service import log_audit_event
        await log_audit_event(
            session=session,
            user_id=str(current_user.user_id),
            user_name=current_user.full_name,
            user_role=current_user.role,
            action="DOCTOR_DELETED",
            resource_type="Doctor",
            resource_id=str(doc.id),
            details={"doctor_name": doc.full_name, "email": doc.email},
        )
    except Exception:
        pass

    await session.commit()

    return DataResponse(
        data={"doctor_id": str(doc.id), "status": "deleted"},
        message=f"Doctor {doc.full_name} deleted successfully",
    )


@router.get(
    "/audit-logs",
    response_model=DataResponse[dict],
    summary="View system audit logs",
)
async def get_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    action: str | None = Query(None),
    search: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_AUDIT_LOGS)),
) -> DataResponse[dict]:
    """Retrieve audit trail of recent platform actions with metrics and optional filtering."""
    from sqlalchemy import or_, func

    query = select(AuditLog)

    if action and action != "ALL":
        query = query.where(AuditLog.action == action)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                AuditLog.action.ilike(search_pattern),
                AuditLog.user_name.ilike(search_pattern),
                AuditLog.user_id.ilike(search_pattern),
                AuditLog.resource_type.ilike(search_pattern),
                AuditLog.details.ilike(search_pattern),
            )
        )

    query = query.order_by(AuditLog.created_at.desc()).limit(limit)
    res = await session.execute(query)
    logs = res.scalars().all()

    # Calculate summary metrics
    tot_query = select(func.count(AuditLog.id))
    tot_res = await session.execute(tot_query)
    total_logs = tot_res.scalar() or 0

    auth_query = select(func.count(AuditLog.id)).where(
        AuditLog.action.in_(["USER_LOGIN", "USER_REGISTER", "PROFILE_UPDATED"])
    )
    auth_res = await session.execute(auth_query)
    auth_count = auth_res.scalar() or 0

    appt_query = select(func.count(AuditLog.id)).where(
        AuditLog.action.in_(["APPOINTMENT_BOOKED", "APPOINTMENT_CANCELLED", "CONSULTATION_SAVED"])
    )
    appt_res = await session.execute(appt_query)
    appt_count = appt_res.scalar() or 0

    admin_query = select(func.count(AuditLog.id)).where(
        AuditLog.action.in_(["DOCTOR_APPROVED", "DOCTOR_DELETED", "DOCTOR_REJECTED"])
    )
    admin_res = await session.execute(admin_query)
    admin_count = admin_res.scalar() or 0

    items = [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "user_name": log.user_name or "System User",
            "user_role": log.user_role or "system",
            "action": log.action,
            "resource_type": log.resource_type,
            "entity_type": log.resource_type,
            "resource_id": str(log.resource_id) if log.resource_id else None,
            "entity_id": str(log.resource_id) if log.resource_id else None,
            "details": log.details,
            "ip_address": log.ip_address or "127.0.0.1",
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]

    return DataResponse(
        data={
            "logs": items,
            "metrics": {
                "total": total_logs,
                "auth": auth_count,
                "appointments": appt_count,
                "admin": admin_count,
            },
        },
        message="Audit logs retrieved successfully",
    )
