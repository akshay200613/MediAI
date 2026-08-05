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
