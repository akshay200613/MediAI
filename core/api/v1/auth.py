"""
Auth API Endpoints – login, register, refresh, logout.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_db
from core.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, RefreshTokenRequest
from core.schemas.base import DataResponse
from core.auth.jwt_handler import (
    hash_password, verify_password, create_token_pair, decode_token
)
from core.models.user import User
from core.repositories.base_repository import BaseRepository
from core.auth.dependencies import CurrentUser, get_current_user

router = APIRouter()


class UserRepository(BaseRepository[User]):
    model = User


@router.post("/login", response_model=DataResponse[TokenResponse], summary="User login")
async def login(
    credentials: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TokenResponse]:
    repo = UserRepository(session)
    user = await repo.get_by_field("email", credentials.email)

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    access_token, refresh_token = create_token_pair(
        str(user.id), user.email, user.role
    )

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
        "role": "user",
        "domain": "platform",
    })

    return DataResponse(
        data={"id": str(user.id), "email": user.email},
        message="Registration successful",
    )


@router.post("/refresh", response_model=DataResponse[TokenResponse], summary="Refresh access token")
async def refresh_token(
    body: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TokenResponse]:
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
        payload["sub"], payload["email"], payload["role"]
    )

    return DataResponse(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        ),
        message="Token refreshed",
    )


@router.get("/me", response_model=DataResponse[dict], summary="Get current user details and role info")
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Resolve current user role, verification status, and linked doctor/patient ID."""
    from uuid import UUID
    from sqlalchemy import select
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

    # Check for patient record
    pat_res = await session.execute(
        select(Patient).where(
            Patient.email == current_user.email,
            Patient.is_deleted == False,
        )
    )
    pat = pat_res.scalar_one_or_none()
    if pat:
        patient_id = str(pat.id)

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
        str(user.id), user.email, user.role
    )

    return DataResponse(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        ),
        message="Google authentication successful",
    )

