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
from core.ai.graph.tools.context import get_tool_security_context


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
    from domains.medai.services.patient_service import (
        PatientService,
    )

    ctx = get_tool_security_context()
    effective_patient_id = patient_id

    try:
        async with AsyncSessionLocal() as session:
            # Authorization / IDOR Protection
            if ctx and ctx.role in ("patient", "user"):
                pat_svc = PatientService(session)
                pat_record = await pat_svc.get_patient_by_user_id(ctx.user_id, user_email=ctx.email)
                valid_ids = {ctx.user_id}
                if pat_record:
                    valid_ids.add(str(pat_record.id))
                if ctx.patient_id:
                    valid_ids.add(str(ctx.patient_id))

                if str(patient_id) not in valid_ids:
                    logger.warning(
                        "Tool IDOR attempt blocked in list_appointments",
                        caller_user_id=ctx.user_id,
                        attempted_patient_id=patient_id,
                    )
                    return {
                        "count": 0,
                        "appointments": [],
                        "error": "Unauthorized: Cannot access appointments for another patient.",
                    }
                effective_patient_id = str(pat_record.id) if pat_record else str(patient_id)

            service = AppointmentService(session)

            appointments = await service.get_by_patient(effective_patient_id)

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
    from domains.medai.services.patient_service import (
        PatientService,
    )
    from domains.medai.schemas.appointment import AppointmentCreate
    from datetime import datetime
    import uuid

    ctx = get_tool_security_context()
    target_patient_id = patient_id

    try:
        async with AsyncSessionLocal() as session:
            # Authorization / IDOR Protection: Override / Validate patient_id for patient role
            if ctx and ctx.role in ("patient", "user"):
                pat_svc = PatientService(session)
                pat_record = await pat_svc.get_patient_by_user_id(ctx.user_id, user_email=ctx.email)
                if pat_record:
                    target_patient_id = str(pat_record.id)
                elif ctx.patient_id:
                    target_patient_id = str(ctx.patient_id)
                else:
                    target_patient_id = str(ctx.user_id)

                if patient_id and str(patient_id) != target_patient_id:
                    logger.info(
                        "Corrected LLM-generated patient_id to authenticated caller patient_id",
                        caller_user_id=ctx.user_id,
                        llm_patient_id=patient_id,
                        actual_patient_id=target_patient_id,
                    )

            service = AppointmentService(session)

            create_data = AppointmentCreate(
                patient_id=target_patient_id,
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
            "error": str(exc),
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
    from domains.medai.services.patient_service import (
        PatientService,
    )
    import uuid

    ctx = get_tool_security_context()

    try:
        async with AsyncSessionLocal() as session:
            service = AppointmentService(session)
            appt_uuid = uuid.UUID(appointment_id)

            existing_appt = await service.get_appointment(appt_uuid)
            if existing_appt is None:
                return {
                    "success": False,
                    "error": f"Appointment {appointment_id} not found",
                }

            # Authorization Check
            if ctx and ctx.role in ("patient", "user"):
                pat_svc = PatientService(session)
                pat_record = await pat_svc.get_patient_by_user_id(ctx.user_id, user_email=ctx.email)
                valid_patient_ids = {ctx.user_id}
                if pat_record:
                    valid_patient_ids.add(str(pat_record.id))
                if ctx.patient_id:
                    valid_patient_ids.add(str(ctx.patient_id))

                if str(existing_appt.patient_id) not in valid_patient_ids:
                    logger.warning(
                        "Tool IDOR attempt blocked in cancel_appointment",
                        caller_user_id=ctx.user_id,
                        appointment_id=appointment_id,
                        appointment_patient_id=str(existing_appt.patient_id),
                    )
                    return {
                        "success": False,
                        "error": "Unauthorized: You can only cancel your own appointments.",
                    }

            appointment = await service.cancel_appointment(
                appt_uuid
            )

            if appointment is None:
                return {
                    "success": False,
                    "error": (
                        f"Appointment {appointment_id} not found"
                    ),
                }

            await session.commit()

            try:
                from domains.medai.websockets.manager import manager
                await manager.notify_appointment_event(
                    "appointment_cancelled",
                    appointment.model_dump(mode="json"),
                    patient_id=str(appointment.patient_id),
                    doctor_id=str(appointment.doctor_id),
                )
            except Exception as e:
                logger.warning(f"WebSocket broadcast failed: {e}")

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
    name: str | None = None,
) -> dict[str, Any]:
    """
    Check doctor availability and schedule information.

    Args:
        doctor_id: Optional specific doctor's UUID.
        specialty: Optional specialty to filter available doctors.
        name: Optional name of the doctor to search for.

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

            if name:
                doctors = await service.search_doctors(name)
            else:
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
