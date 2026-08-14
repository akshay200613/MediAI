"""
Create or update the MediAI administrator account.

Usage:
    python -m scripts.create_admin
"""

import asyncio

from sqlalchemy import select

from core.auth.jwt_handler import hash_password
from core.config.settings import settings
from core.database.base import AsyncSessionLocal
from core.models.user import User


async def create_or_update_admin() -> None:
    """Create or update the configured MediAI administrator."""

    if not settings.admin_email:
        raise ValueError("ADMIN_EMAIL is not configured.")

    if not settings.admin_password:
        raise ValueError("ADMIN_PASSWORD is not configured.")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == settings.admin_email)
        )

        admin = result.scalar_one_or_none()

        if admin:
            admin.hashed_password = hash_password(settings.admin_password)
            admin.full_name = settings.admin_full_name
            admin.role = "admin"
            admin.domain = "platform"
            admin.is_active = True
            admin.is_verified = True

            await session.commit()

            print("Admin account updated successfully.")
            print(f"Email: {settings.admin_email}")
            return

        admin = User(
            email=settings.admin_email,
            hashed_password=hash_password(settings.admin_password),
            full_name=settings.admin_full_name,
            role="admin",
            domain="platform",
            is_active=True,
            is_verified=True,
        )

        session.add(admin)

        await session.commit()

        print("Admin account created successfully.")
        print(f"Email: {settings.admin_email}")


if __name__ == "__main__":
    asyncio.run(create_or_update_admin())
    