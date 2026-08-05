"""Appointment Pydantic schemas."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import Field
from core.schemas.base import BaseSchema, TimestampSchema


class AppointmentCreate(BaseSchema):
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    appointment_type: str = "consultation"
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, ge=10, le=180)
    reason: Optional[str] = None
    notes: Optional[str] = None


class AppointmentUpdate(BaseSchema):
    appointment_type: Optional[str] = None
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    reason: Optional[str] = None
    notes: Optional[str] = None


class AppointmentOut(TimestampSchema):
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    appointment_type: str
    status: str
    scheduled_at: datetime
    duration_minutes: int
    reason: Optional[str] = None
    notes: Optional[str] = None
    ai_triage_summary: Optional[str] = None
    is_deleted: bool = False
