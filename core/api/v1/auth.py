"""
Auth API Endpoints – login, register, refresh, logout.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_db
from core.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, RefreshTokenRequest
from core.schemas.base import DataResponse
from core.auth.jwt_handler import (
    hash_password, verify_password, create_token_pair, decode_token
)
from core.models.user import User
from domains.medai.models.doctor import Doctor
from domains.medai.models.patient import Patient
from fastapi.security import HTTPAuthorizationCredentials
from core.repositories.base_repository import BaseRepository
from core.auth.dependencies import CurrentUser, get_current_user, require_roles, bearer_scheme
from core.metrics import auth_login_total

router = APIRouter()

# Global tracking set for pending password reset requests requiring Admin approval
PENDING_PASSWORD_RESET_USER_IDS: set[str] = set()


class UserRepository(BaseRepository[User]):
    model = User


@router.post("/login", response_model=DataResponse[TokenResponse], summary="User login")
async def login(
    credentials: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TokenResponse]:
    repo = UserRepository(session)
    user = await repo.get_by_field("email", credentials.email)

    if not user:
        auth_login_total.labels(outcome="unknown_user").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if user has a pending password reset request requiring admin approval
    if str(user.id) in PENDING_PASSWORD_RESET_USER_IDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your password reset request is pending Admin approval. You will be able to log in once Admin approves and sets your new password.",
        )

    if not verify_password(credentials.password, user.hashed_password):
        auth_login_total.labels(outcome="wrong_password").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        auth_login_total.labels(outcome="disabled").inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    auth_login_total.labels(outcome="success").inc()
    access_token, refresh_token = create_token_pair(
        str(user.id), user.email, user.role, user.full_name
    )

    # Log successful login to Audit Trail
    try:
        from core.services.audit_service import log_audit_event
        await log_audit_event(
            session=session,
            user_id=str(user.id),
            user_name=user.full_name,
            user_role=user.role,
            action="USER_LOGIN",
            resource_type="User",
            resource_id=str(user.id),
            details={"email": user.email, "role": user.role},
        )
        await session.commit()
    except Exception:
        pass

    from core.config.settings import settings
    return DataResponse(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        ),
        message="Login successful",
    )


@router.post("/register", response_model=DataResponse[dict], status_code=201, summary="Register user")
async def register(
    data: RegisterRequest,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    repo = UserRepository(session)

    if await repo.exists("email", data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = await repo.create({
        "email": data.email,
        "hashed_password": hash_password(data.password),
        "full_name": data.full_name,
        "role": "patient",
        "domain": "platform",
    })

    # Auto-create Patient profile record
    from domains.medai.models.patient import Patient
    names = data.full_name.split(" ", 1)
    first_name = names[0]
    last_name = names[1] if len(names) > 1 else ""
    pat = Patient(
        first_name=first_name,
        last_name=last_name,
        email=data.email,
        phone="000-000-0000",
        user_id=str(user.id),
    )
    session.add(pat)

    # Log registration to Audit Trail
    try:
        from core.services.audit_service import log_audit_event
        await log_audit_event(
            session=session,
            user_id=str(user.id),
            user_name=data.full_name,
            user_role="patient",
            action="USER_REGISTER",
            resource_type="User",
            resource_id=str(user.id),
            details={"email": data.email, "full_name": data.full_name},
        )
    except Exception:
        pass

    await session.commit()

    return DataResponse(
        data={"id": str(user.id), "email": user.email},
        message="Registration successful",
    )


@router.post("/refresh", response_model=DataResponse[TokenResponse], summary="Refresh access token")
async def refresh_token(
    body: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TokenResponse]:
    from core.auth.token_blacklist import is_token_blacklisted
    if await is_token_blacklisted(body.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    from core.config.settings import settings
    access_token, new_refresh_token = create_token_pair(
        payload["sub"], payload["email"], payload["role"], payload.get("full_name")
    )

    return DataResponse(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        ),
        message="Token refreshed",
    )


@router.post("/logout", response_model=DataResponse[dict], summary="User logout and token revocation")
async def logout(
    body: RefreshTokenRequest | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> DataResponse[dict]:
    """Revoke active access and refresh tokens to prevent reuse."""
    from core.auth.token_blacklist import blacklist_token
    from core.config.settings import settings

    access_ttl = settings.jwt_access_token_expire_minutes * 60
    refresh_ttl = settings.jwt_refresh_token_expire_days * 86400

    # Blacklist the current bearer access token
    await blacklist_token(credentials.credentials, expires_in_seconds=access_ttl)

    # Blacklist the provided refresh token if present
    if body and body.refresh_token:
        await blacklist_token(body.refresh_token, expires_in_seconds=refresh_ttl)

    return DataResponse(
        data={"revoked": True},
        message="Successfully logged out",
    )


@router.get("/me", response_model=DataResponse[dict], summary="Get current user details and role info")
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Resolve current user role, verification status, and linked doctor/patient ID."""
    from uuid import UUID
    from sqlalchemy import select, or_
    from domains.medai.models.doctor import Doctor
    from domains.medai.models.patient import Patient

    repo = UserRepository(session)
    user = await repo.get_by_id(UUID(current_user.user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    doctor_id = None
    patient_id = None

    # Check for doctor record
    doc_res = await session.execute(
        select(Doctor).where(
            Doctor.user_id == current_user.user_id,
            Doctor.is_deleted == False,
        )
    )
    doc = doc_res.scalar_one_or_none()
    if doc:
        doctor_id = str(doc.id)

    # Check for patient record (by user_id OR email)
    pat_res = await session.execute(
        select(Patient).where(
            or_(
                Patient.user_id == current_user.user_id,
                Patient.email == current_user.email,
            ),
            Patient.is_deleted == False,
        )
    )
    pat = pat_res.scalar_one_or_none()
    if pat:
        patient_id = str(pat.id)
        if not pat.user_id:
            pat.user_id = current_user.user_id
            await session.commit()
    elif user.role in ("user", "patient"):
        # Auto-create Patient record if user doesn't have one yet
        names = (user.full_name or "Patient").split(" ", 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else ""
        new_pat = Patient(
            first_name=first_name,
            last_name=last_name,
            email=user.email,
            phone="000-000-0000",
            user_id=str(user.id),
        )
        session.add(new_pat)
        await session.commit()
        patient_id = str(new_pat.id)

    return DataResponse(
        data={
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "domain": user.domain,
            "doctor_id": doctor_id,
            "patient_id": patient_id,
            "is_verified": user.is_verified,
        },
        message="User details retrieved",
    )



@router.post("/google", response_model=DataResponse[TokenResponse], summary="Google OAuth login or registration")
async def google_auth(
    body: dict,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TokenResponse]:
    """
    Simulate/Handle Google OAuth authentication.
    If requested role is doctor, sets user as unverified pending admin approval.
    """
    from core.config.settings import settings
    from domains.medai.models.doctor import Doctor
    from domains.medai.models.patient import Patient
    import uuid

    email = body.get("email", "").strip().lower()
    full_name = body.get("full_name", "Google User").strip()
    requested_role = body.get("requested_role", "patient").strip().lower()

    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    repo = UserRepository(session)
    user = await repo.get_by_field("email", email)

    if not user:
        # Determine initial role & verification
        is_verified = True
        assigned_role = requested_role if requested_role in ["patient", "doctor", "admin"] else "patient"

        if requested_role == "doctor":
            # Doctors land in pending verification state
            is_verified = False
            assigned_role = "user"  # demoted until approved

        user = await repo.create({
            "email": email,
            "hashed_password": hash_password(str(uuid.uuid4())),
            "full_name": full_name,
            "role": assigned_role,
            "domain": "medai",
            "is_verified": is_verified,
        })

        # Auto-create Patient record if patient
        if requested_role == "patient":
            names = full_name.split(" ", 1)
            first_name = names[0]
            last_name = names[1] if len(names) > 1 else ""
            pat = Patient(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone="000-000-0000",
                user_id=str(user.id),  # Link to auth user so we can scope appointments
            )
            session.add(pat)
            await session.commit()

        # Create Pending Doctor record if doctor requested
        elif requested_role == "doctor":
            names = full_name.split(" ", 1)
            first_name = names[0]
            last_name = names[1] if len(names) > 1 else ""
            doc = Doctor(
                user_id=str(user.id),
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone="000-000-0000",
                specialty=body.get("specialty", "General Medicine"),
                license_number=f"LIC-PENDING-{uuid.uuid4().hex[:6].upper()}",
                is_available=False,
            )
            session.add(doc)
            await session.commit()

    access_token, refresh_token = create_token_pair(
        str(user.id), user.email, user.role, user.full_name
    )

    return DataResponse(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        ),
        message="Google authentication successful",
    )


@router.post(
    "/register-doctor",
    response_model=DataResponse[dict],
    status_code=201,
    summary="Doctor self-registration — creates pending verification account",
)
async def register_doctor(
    body: dict,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """
    Doctor self-registration endpoint.
    Creates a User with role='user', is_verified=False and a linked Doctor record.
    Admin must approve before the doctor can access the doctor dashboard.
    """
    import uuid as uuid_lib
    from domains.medai.models.doctor import Doctor

    email = (body.get("email") or "").strip().lower()
    password = (body.get("password") or "").strip()
    full_name = (body.get("full_name") or "").strip()
    name_parts = full_name.split(" ", 1)
    first_name = (body.get("first_name") or name_parts[0]).strip()
    last_name = (body.get("last_name") or (name_parts[1] if len(name_parts) > 1 else "")).strip()
    phone = (body.get("phone") or "000-000-0000").strip()
    specialty = (body.get("specialty") or "General Medicine").strip()
    license_number = (body.get("license_number") or "").strip()
    years_of_experience = int(body.get("years_of_experience") or 0)
    bio = (body.get("bio") or "").strip() or None
    consultation_fee = float(body.get("consultation_fee") or 0.0)
    available_days = (body.get("available_days") or "").strip() or None
    working_hours_start = (str(body.get("working_hours_start") or "")[:5]) or None
    working_hours_end = (str(body.get("working_hours_end") or "")[:5]) or None

    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not license_number:
        raise HTTPException(status_code=400, detail="License number is required")

    repo = UserRepository(session)
    if await repo.exists("email", email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address is already registered.",
        )

    # Check for duplicate license number
    lic_res = await session.execute(select(Doctor).where(Doctor.license_number == license_number))
    if lic_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A doctor with this license number is already registered.",
        )

    # Create user in pending verification state (role='doctor', is_verified=False)
    user = await repo.create({
        "email": email,
        "hashed_password": hash_password(password),
        "full_name": full_name or f"{first_name} {last_name}".strip(),
        "role": "doctor",
        "domain": "medai",
        "is_verified": False,
    })

    # Create the Doctor profile record
    doc = Doctor(
        user_id=str(user.id),
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        specialty=specialty,
        license_number=license_number,
        years_of_experience=years_of_experience,
        bio=bio,
        consultation_fee=consultation_fee,
        available_days=available_days,
        working_hours_start=working_hours_start,
        working_hours_end=working_hours_end,
        is_available=False,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    return DataResponse(
        data={
            "id": str(user.id),
            "email": user.email,
            "doctor_id": str(doc.id),
            "status": "pending_approval",
        },
        message=(
            "Doctor registration submitted successfully! "
            "Your account is pending administrator approval before dashboard access is enabled."
        ),
    )


@router.get("/profile", response_model=DataResponse[dict], summary="Get logged-in user profile details")
async def get_profile(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Get full profile details for the authenticated user (including doctor or patient record if applicable)."""
    from sqlalchemy import select
    from domains.medai.models.doctor import Doctor
    from domains.medai.models.patient import Patient

    repo = UserRepository(session)
    user = await repo.get_by_id(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    doctor_data = None
    patient_data = None

    # Check for doctor record
    doc_res = await session.execute(
        select(Doctor).where(Doctor.user_id == str(user.id), Doctor.is_deleted == False)
    )
    doc = doc_res.scalar_one_or_none()
    if doc:
        doctor_data = {
            "id": str(doc.id),
            "first_name": doc.first_name,
            "last_name": doc.last_name,
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
            "is_available": doc.is_available,
        }

    # Check for patient record
    pat_res = await session.execute(
        select(Patient).where(
            (Patient.email == user.email) | (Patient.user_id == str(user.id)),
            Patient.is_deleted == False
        )
    )
    pat = pat_res.scalar_one_or_none()
    if pat:
        patient_data = {
            "id": str(pat.id),
            "first_name": pat.first_name,
            "last_name": pat.last_name,
            "full_name": pat.full_name,
            "email": pat.email,
            "phone": pat.phone,
            "date_of_birth": pat.date_of_birth.isoformat() if pat.date_of_birth else None,
            "gender": pat.gender,
            "blood_group": pat.blood_group,
            "address": pat.address,
            "city": pat.city,
            "state": pat.state,
            "allergies": pat.allergies,
            "chronic_conditions": pat.chronic_conditions,
            "emergency_contact_name": pat.emergency_contact_name,
            "emergency_contact_phone": pat.emergency_contact_phone,
        }

    return DataResponse(
        data={
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "domain": user.domain,
                "is_verified": user.is_verified,
            },
            "doctor": doctor_data,
            "patient": patient_data,
        },
        message="Profile retrieved",
    )


@router.patch("/profile", response_model=DataResponse[dict], summary="Update logged-in user profile")
async def update_profile(
    body: dict,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Update profile details for the authenticated user and linked doctor/patient records."""
    from sqlalchemy import select
    from datetime import date
    from domains.medai.models.doctor import Doctor
    from domains.medai.models.patient import Patient

    repo = UserRepository(session)
    user = await repo.get_by_id(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update User base attributes
    if "full_name" in body and body["full_name"]:
        user.full_name = str(body["full_name"]).strip()

    # Update linked Doctor record if user is a doctor or has doctor record
    doc_res = await session.execute(
        select(Doctor).where(Doctor.user_id == str(user.id), Doctor.is_deleted == False)
    )
    doc = doc_res.scalar_one_or_none()
    if doc:
        if "full_name" in body:
            parts = str(body["full_name"]).strip().split(" ", 1)
            doc.first_name = parts[0]
            doc.last_name = parts[1] if len(parts) > 1 else ""
        if "phone" in body:
            doc.phone = str(body["phone"]).strip()
        if "specialty" in body:
            doc.specialty = str(body["specialty"]).strip()
        if "years_of_experience" in body:
            doc.years_of_experience = int(body["years_of_experience"] or 0)
        if "bio" in body:
            doc.bio = str(body["bio"]).strip() if body["bio"] else None
        if "consultation_fee" in body:
            doc.consultation_fee = float(body["consultation_fee"] or 0.0)
        if "available_days" in body:
            doc.available_days = str(body["available_days"]).strip() if body["available_days"] else None
        if "working_hours_start" in body:
            doc.working_hours_start = str(body["working_hours_start"]).strip() if body["working_hours_start"] else None
        if "working_hours_end" in body:
            doc.working_hours_end = str(body["working_hours_end"]).strip() if body["working_hours_end"] else None
        if "is_available" in body:
            doc.is_available = bool(body["is_available"])

    # Update linked Patient record if user is a patient or has patient record
    pat_res = await session.execute(
        select(Patient).where(
            (Patient.email == user.email) | (Patient.user_id == str(user.id)),
            Patient.is_deleted == False
        )
    )
    pat = pat_res.scalar_one_or_none()
    if not pat and current_user.role in ("patient", "user"):
        # Auto-create patient record if not exists
        parts = user.full_name.split(" ", 1)
        pat = Patient(
            user_id=str(user.id),
            first_name=parts[0],
            last_name=parts[1] if len(parts) > 1 else "",
            email=user.email,
            phone=body.get("phone", "000-000-0000"),
        )
        session.add(pat)

    if pat:
        if "full_name" in body:
            parts = str(body["full_name"]).strip().split(" ", 1)
            pat.first_name = parts[0]
            pat.last_name = parts[1] if len(parts) > 1 else ""
        if "phone" in body:
            pat.phone = str(body["phone"]).strip()
        if "date_of_birth" in body and body["date_of_birth"]:
            try:
                pat.date_of_birth = date.fromisoformat(str(body["date_of_birth"]).split("T")[0])
            except Exception:
                pass
        if "gender" in body:
            pat.gender = str(body["gender"]).strip() if body["gender"] else None
        if "blood_group" in body:
            pat.blood_group = str(body["blood_group"]).strip() if body["blood_group"] else None
        if "address" in body:
            pat.address = str(body["address"]).strip() if body["address"] else None
        if "city" in body:
            pat.city = str(body["city"]).strip() if body["city"] else None
        if "state" in body:
            pat.state = str(body["state"]).strip() if body["state"] else None
        if "allergies" in body:
            pat.allergies = str(body["allergies"]).strip() if body["allergies"] else None
        if "chronic_conditions" in body:
            pat.chronic_conditions = str(body["chronic_conditions"]).strip() if body["chronic_conditions"] else None
        if "emergency_contact_name" in body:
            pat.emergency_contact_name = str(body["emergency_contact_name"]).strip() if body["emergency_contact_name"] else None
        if "emergency_contact_phone" in body:
            pat.emergency_contact_phone = str(body["emergency_contact_phone"]).strip() if body["emergency_contact_phone"] else None

    await session.commit()

    return DataResponse(
        data={"updated": True},
        message="Profile updated successfully",
    )


@router.post("/change-password", response_model=DataResponse[dict], summary="Change password for logged-in user")
async def change_password(
    body: dict,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Change account password for current authenticated user."""
    current_pwd = str(body.get("current_password", "")).strip()
    new_pwd = str(body.get("new_password", "")).strip()

    if not current_pwd or not new_pwd:
        raise HTTPException(status_code=400, detail="Current password and new password are required")
    if len(new_pwd) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    repo = UserRepository(session)
    user = await repo.get_by_id(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(current_pwd, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.hashed_password = hash_password(new_pwd)
    await session.commit()

    return DataResponse(data={"success": True}, message="Password updated successfully")


@router.post("/forgot-password", response_model=DataResponse[dict], summary="Request password reset — notifies admin")
async def forgot_password(
    body: dict,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Notify administrator that user/doctor has requested a password reset and locks login until Admin approves."""
    from domains.medai.websockets.manager import manager

    email = (body.get("email") or "").strip().lower()

    if not email:
        raise HTTPException(status_code=400, detail="Email address is required")

    repo = UserRepository(session)
    user = await repo.get_by_field("email", email)
    if not user:
        return DataResponse(
            data={"email": email, "status": "submitted"},
            message="Password reset request submitted. Admin has been notified to assist with credential reset."
        )

    # Mark password reset request as pending admin approval
    PENDING_PASSWORD_RESET_USER_IDS.add(str(user.id))

    # Broadcast real-time alert to all online Admins via WebSockets
    try:
        await manager.notify_admin_password_reset_request(
            user_id=str(user.id),
            email=user.email,
            full_name=user.full_name,
        )
    except Exception:
        pass

    return DataResponse(
        data={"email": user.email, "user_id": str(user.id), "status": "pending_admin_approval"},
        message="Password reset request submitted to Admin! Admin has been notified to approve your request and set your new password."
    )


@router.get("/pending-password-resets", response_model=DataResponse[list[dict]], summary="List pending password reset requests for admin")
async def list_pending_password_resets(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_roles("admin", "super_admin")),
) -> DataResponse[list[dict]]:
    """Return all users/doctors with pending password reset requests."""
    from uuid import UUID
    repo = UserRepository(session)
    pending_list = []
    for uid in list(PENDING_PASSWORD_RESET_USER_IDS):
        try:
            user = await repo.get_by_id(UUID(uid))
            if user:
                pending_list.append({
                    "user_id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                })
        except Exception:
            pass
    return DataResponse(data=pending_list, message="Retrieved pending password reset requests")


@router.post("/admin-reset-password", response_model=DataResponse[dict], summary="Admin approve & reset doctor/user password")
async def admin_reset_password(
    body: dict,
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("admin", "super_admin")),
) -> DataResponse[dict]:
    """Admin endpoint to approve password reset request and set new password for doctor/user."""
    from uuid import UUID
    from domains.medai.websockets.manager import manager

    user_id = (body.get("user_id") or "").strip()
    email = (body.get("email") or "").strip().lower()
    new_password = (body.get("new_password") or "").strip()

    if not new_password or len(new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters long")

    repo = UserRepository(session)
    user = None
    if user_id:
        try:
            user = await repo.get_by_id(UUID(user_id))
        except Exception:
            pass
    if not user and email:
        user = await repo.get_by_field("email", email)

    if not user:
        raise HTTPException(status_code=404, detail="Target user account not found")

    user.hashed_password = hash_password(new_password)
    user.is_active = True
    user.is_verified = True

    # Clear pending password reset status upon admin approval
    PENDING_PASSWORD_RESET_USER_IDS.discard(str(user.id))

    await session.commit()

    # Notify doctor via WebSocket
    try:
        await manager.notify_doctor_updated(
            doctor_id=str(user.id),
            doctor_data={"email": user.email},
            changes_summary=f"Admin ({current_user.full_name or 'System'}) has approved your password reset request and set your new password. You can now sign in.",
        )
    except Exception:
        pass

    return DataResponse(
        data={"user_id": str(user.id), "email": user.email},
        message=f"Password reset request approved and new password set for {user.email} by Admin."
    )



