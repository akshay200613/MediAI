"""
FastAPI Auth Dependencies – current user extraction and role guards.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.auth.jwt_handler import decode_token
from core.config.logging import get_logger

logger = get_logger(__name__)
bearer_scheme = HTTPBearer()


class CurrentUser:
    """Represents the authenticated user extracted from the JWT."""
    def __init__(self, user_id: str, email: str, role: str) -> None:
        self.user_id = user_id
        self.email = email
        self.role = role


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    """
    FastAPI dependency: extracts and validates the JWT bearer token.
    Raises 401 if invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
        user_id: str = payload.get("sub", "")
        email: str = payload.get("email", "")
        role: str = payload.get("role", "user")
        if not user_id:
            raise credentials_exception
        return CurrentUser(user_id=user_id, email=email, role=role)
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
