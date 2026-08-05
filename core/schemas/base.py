"""
Base Pydantic schemas shared across the entire platform.
"""

import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with orm_mode enabled."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class BaseResponse(BaseSchema):
    """Standard API response envelope."""
    success: bool = True
    message: str = "OK"


class DataResponse(BaseResponse, Generic[T]):
    """Single-item response."""
    data: T


class PaginatedResponse(BaseResponse, Generic[T]):
    """Paginated list response."""
    data: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(BaseSchema):
    """Standard error response."""
    success: bool = False
    message: str
    detail: Any = None
    error_code: str | None = None


class TimestampSchema(BaseSchema):
    """Mixin for models with created/updated timestamps."""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
