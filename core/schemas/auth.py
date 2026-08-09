"""
Auth-related Pydantic schemas.
"""

import uuid

from pydantic import EmailStr, Field

from core.schemas.base import BaseSchema


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str = Field(min_length=8)


class RegisterRequest(BaseSchema):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=255)


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseSchema):
    refresh_token: str


class UserOut(BaseSchema):
    """Safe user representation (no password)."""
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    domain: str
    is_active: bool
    is_verified: bool
    avatar_url: str | None = None
