"""
Appointment MCP Tool – check availability and book appointments.
"""

from datetime import datetime
from core.config.logging import get_logger

logger = get_logger("medai.mcp.appointment_tool")


async def check_availability(doctor_id: str, date: str) -> dict:
    """
    Check a doctor's appointment availability for a given date.

    Args:
        doctor_id: UUID of the doctor
        date: Date in YYYY-MM-DD format

    Returns:
        Dict with available time slots
    """
    # TODO: Query real appointment DB
    logger.info("Checking availability", doctor_id=doctor_id, date=date)
    return {
        "doctor_id": doctor_id,
        "date": date,
        "available_slots": [
            "09:00", "09:30", "10:00", "10:30",
            "14:00", "14:30", "15:00", "15:30",
        ],
        "booked_slots": ["11:00", "11:30"],
    }


async def book_appointment(
    patient_id: str,
    doctor_id: str,
    scheduled_at: str,
    reason: str = "",
) -> dict:
    """
    Book an appointment for a patient with a doctor.

    Args:
        patient_id: UUID of the patient
        doctor_id: UUID of the doctor
        scheduled_at: ISO datetime string (e.g., "2024-01-15T09:00:00")
        reason: Reason for the appointment

    Returns:
        Booking confirmation with appointment ID
    """
    logger.info("Booking appointment", patient_id=patient_id, doctor_id=doctor_id)
    return {
        "success": True,
        "appointment_id": "apt-placeholder-id",
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "scheduled_at": scheduled_at,
        "reason": reason,
        "status": "scheduled",
        "message": "Appointment booked successfully",
    }
