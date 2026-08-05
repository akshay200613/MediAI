"""
Global FastAPI Dependencies.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_db
from core.auth.dependencies import CurrentUser, get_current_user


async def get_session(session: AsyncSession = Depends(get_db)) -> AsyncSession:
    """Database session dependency alias."""
    return session


async def get_authenticated_user(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Authenticated user dependency alias."""
    return current_user
