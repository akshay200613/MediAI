"""
Patient Pydantic schemas – request/response validation.
"""

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import EmailStr, Field

from core.schemas.base import BaseSchema, TimestampSchema


class PatientCreate(BaseSchema):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=7, max_length=20)
    email: Optional[EmailStr] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class PatientUpdate(BaseSchema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None


class PatientOut(TimestampSchema):
    first_name: str
    last_name: str
    full_name: str = ""
    email: Optional[str] = None
    phone: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    is_deleted: bool = False
