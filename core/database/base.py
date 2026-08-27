"""
Database Layer – SQLAlchemy async engine, Base, and session factory.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from core.config.settings import settings


# ── Engine ─────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_timeout=30,
)

# ── Session Factory ────────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Declarative Base ───────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """All SQLAlchemy models inherit from this Base."""
    pass
