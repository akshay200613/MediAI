"""Doctor Pydantic schemas."""
import uuid
from typing import Optional
from pydantic import EmailStr, Field
from core.schemas.base import BaseSchema, TimestampSchema


class DoctorCreate(BaseSchema):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)
    specialty: str = Field(min_length=2, max_length=100)
    license_number: str = Field(min_length=3, max_length=100)
    years_of_experience: int = Field(default=0, ge=0)
    bio: Optional[str] = None
    consultation_fee: float = Field(default=0.0, ge=0)
    available_days: Optional[str] = None   # e.g. "Mon,Tue,Wed,Thu,Fri"
    working_hours_start: Optional[str] = None  # "09:00"
    working_hours_end: Optional[str] = None    # "17:00"


class DoctorUpdate(BaseSchema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    specialty: Optional[str] = None
    bio: Optional[str] = None
    consultation_fee: Optional[float] = None
    available_days: Optional[str] = None
    working_hours_start: Optional[str] = None
    working_hours_end: Optional[str] = None
    is_available: Optional[bool] = None


class DoctorOut(TimestampSchema):
    first_name: str
    last_name: str
    full_name: str = ""
    email: str
    phone: str
    specialty: str
    license_number: str
    years_of_experience: int
    bio: Optional[str] = None
    consultation_fee: float
    available_days: Optional[str] = None
    working_hours_start: Optional[str] = None
    working_hours_end: Optional[str] = None
    is_available: bool
    is_deleted: bool = False
