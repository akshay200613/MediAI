"""
FastAPI Auth Dependencies – current user extraction and role guards.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.auth.jwt_handler import decode_token
from core.auth.token_blacklist import is_token_blacklisted
from core.config.logging import get_logger

logger = get_logger(__name__)
bearer_scheme = HTTPBearer()


class CurrentUser:
    """Represents the authenticated user extracted from the JWT."""
    def __init__(self, user_id: str, email: str, role: str, full_name: str | None = None) -> None:
        self.user_id = user_id
        self.email = email
        self.role = role
        if full_name:
            self.full_name = full_name
        elif email:
            self.full_name = email.split("@")[0].capitalize()
        else:
            self.full_name = "User"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    """
    FastAPI dependency: extracts and validates the JWT bearer token.
    Raises 401 if invalid or revoked.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    raw_token = credentials.credentials
    if await is_token_blacklisted(raw_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(raw_token)
        
        # Security: Enforce access token type to prevent refresh token reuse
        if payload.get("type") != "access":
            raise credentials_exception
            
        user_id: str = payload.get("sub", "")
        email: str = payload.get("email", "")
        role: str = payload.get("role", "user")
        full_name: str | None = payload.get("full_name")
        
        if not user_id:
            raise credentials_exception
        return CurrentUser(user_id=user_id, email=email, role=role, full_name=full_name)
    except ValueError:
        raise credentials_exception


def require_roles(*roles: str):
    """
    Dependency factory: raises 403 if the current user's role is not in `roles`.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_roles("admin", "super_admin"))])
    """
    async def _guard(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {roles}",
            )
        return current_user
    return _guard
