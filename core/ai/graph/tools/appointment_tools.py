"""
Appointment Tools – MCP-compatible tools for appointment management.

Wraps the existing ``AppointmentService`` and ``DoctorService``
to expose scheduling capabilities to LangGraph agents.

Tools:

    list_appointments       → List appointments for a patient
    book_appointment        → Create a new appointment
    cancel_appointment      → Cancel an existing appointment
    get_doctor_availability → Check a doctor's available slots
"""

from __future__ import annotations

from typing import Any

from core.ai.graph.tools.server import mcp_server
from core.config.logging import get_logger
from core.database.base import AsyncSessionLocal


logger = get_logger(__name__)


@mcp_server.tool()
async def list_appointments(
    patient_id: str,
    status: str | None = None,
) -> dict[str, Any]:
    """
    List appointments for a specific patient.

    Args:
        patient_id: The patient's UUID string.
        status: Optional filter by status
                (scheduled, confirmed, completed, cancelled).

    Returns:
        List of appointments with details.
    """

    from domains.medai.services.appointment_service import (
        AppointmentService,
    )

    try:
        async with AsyncSessionLocal() as session:
            service = AppointmentService(session)

            appointments = await service.get_by_patient(patient_id)

            # Filter by status if provided
            if status:
                appointments = [
                    a
                    for a in appointments
                    if a.status == status
                ]

            return {
                "count": len(appointments),
                "appointments": [
                    a.model_dump(mode="json") for a in appointments
                ],
            }

    except Exception as exc:
        logger.error(
            "list_appointments failed",
            patient_id=patient_id,
            error=str(exc),
        )
        return {
            "count": 0,
            "appointments": [],
            "error": f"Failed to list appointments: {exc}",
        }


@mcp_server.tool()
async def book_appointment(
    patient_id: str,
    doctor_id: str,
    scheduled_at: str,
    appointment_type: str = "consultation",
    reason: str = "",
    duration_minutes: int = 30,
) -> dict[str, Any]:
    """
    Book a new appointment.

    Args:
        patient_id: The patient's UUID string.
        doctor_id: The doctor's UUID string.
        scheduled_at: ISO 8601 datetime for the appointment.
        appointment_type: Type of appointment
                          (consultation, follow_up, emergency,
                           lab_test, vaccination).
        reason: Brief reason for the visit.
        duration_minutes: Appointment duration in minutes.

    Returns:
        Created appointment details or error message.
    """

    from domains.medai.services.appointment_service import (
        AppointmentService,
    )
    from domains.medai.schemas.appointment import AppointmentCreate
    from datetime import datetime

    try:
        async with AsyncSessionLocal() as session:
            service = AppointmentService(session)

            create_data = AppointmentCreate(
                patient_id=patient_id,
                doctor_id=doctor_id,
                scheduled_at=datetime.fromisoformat(scheduled_at),
                appointment_type=appointment_type,
                reason=reason,
                duration_minutes=duration_minutes,
            )

            appointment = await service.create_appointment(
                create_data
            )

            await session.commit()

            return {
                "success": True,
                "appointment": appointment.model_dump(mode="json"),
            }

    except Exception as exc:
        logger.error(
            "book_appointment failed",
            patient_id=patient_id,
            doctor_id=doctor_id,
            error=str(exc),
        )
        return {
            "success": False,
            "error": f"Failed to book appointment: {exc}",
        }


@mcp_server.tool()
async def cancel_appointment(
    appointment_id: str,
) -> dict[str, Any]:
    """
    Cancel an existing appointment.

    Args:
        appointment_id: The appointment's UUID string.

    Returns:
        Updated appointment details or error message.
    """

    from domains.medai.services.appointment_service import (
        AppointmentService,
    )
    import uuid

    try:
        async with AsyncSessionLocal() as session:
            service = AppointmentService(session)

            appointment = await service.cancel_appointment(
                uuid.UUID(appointment_id)
            )

            if appointment is None:
                return {
                    "success": False,
                    "error": (
                        f"Appointment {appointment_id} not found"
                    ),
                }

            await session.commit()

            return {
                "success": True,
                "appointment": appointment.model_dump(mode="json"),
            }

    except Exception as exc:
        logger.error(
            "cancel_appointment failed",
            appointment_id=appointment_id,
            error=str(exc),
        )
        return {
            "success": False,
            "error": f"Failed to cancel appointment: {exc}",
        }


@mcp_server.tool()
async def get_doctor_availability(
    doctor_id: str | None = None,
    specialty: str | None = None,
) -> dict[str, Any]:
    """
    Check doctor availability and schedule information.

    Args:
        doctor_id: Optional specific doctor's UUID.
        specialty: Optional specialty to filter available doctors.

    Returns:
        List of available doctors with their schedule info.
    """

    from domains.medai.services.doctor_service import DoctorService

    try:
        async with AsyncSessionLocal() as session:
            service = DoctorService(session)

            if doctor_id:
                import uuid
                doctor = await service.get_doctor(
                    uuid.UUID(doctor_id)
                )

                if doctor is None:
                    return {
                        "found": False,
                        "error": (
                            f"Doctor {doctor_id} not found"
                        ),
                    }

                return {
                    "found": True,
                    "doctors": [
                        doctor.model_dump(mode="json"),
                    ],
                }

            # List available doctors, optionally filtered by specialty
            doctors = await service.get_available_doctors(specialty)

            return {
                "count": len(doctors),
                "doctors": [
                    d.model_dump(mode="json") for d in doctors
                ],
            }

    except Exception as exc:
        logger.error(
            "get_doctor_availability failed",
            doctor_id=doctor_id,
            specialty=specialty,
            error=str(exc),
        )
        return {
            "count": 0,
            "doctors": [],
            "error": f"Failed to check availability: {exc}",
        }
