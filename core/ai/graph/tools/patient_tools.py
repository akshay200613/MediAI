"""
Patient Tools – MCP-compatible tools for patient operations.

Wraps the existing ``PatientService`` to expose patient data
to LangGraph agents via the FastMCP server.

Tools:

    get_patient_profile   → Retrieve a patient's profile by ID
    search_patients       → Search patients by name, phone, or email
    get_patient_history   → Get a patient's medical history and
                            past appointments
"""

from __future__ import annotations

from typing import Any

from core.ai.graph.tools.server import mcp_server
from core.config.logging import get_logger
from core.database.base import AsyncSessionLocal
from core.ai.graph.tools.context import get_tool_security_context


logger = get_logger(__name__)


@mcp_server.tool()
async def get_patient_profile(patient_id: str) -> dict[str, Any]:
    """
    Retrieve a patient's profile by their UUID.

    Args:
        patient_id: The patient's UUID string.

    Returns:
        Patient profile data including personal info, contact
        details, medical info (allergies, chronic conditions),
        and emergency contacts.
    """

    from domains.medai.services.patient_service import PatientService
    import uuid

    ctx = get_tool_security_context()

    try:
        async with AsyncSessionLocal() as session:
            service = PatientService(session)

            # Authorization Check
            if ctx and ctx.role in ("patient", "user"):
                pat_record = await service.get_patient_by_user_id(ctx.user_id, user_email=ctx.email)
                valid_ids = {ctx.user_id}
                if pat_record:
                    valid_ids.add(str(pat_record.id))
                if ctx.patient_id:
                    valid_ids.add(str(ctx.patient_id))

                if str(patient_id) not in valid_ids:
                    logger.warning(
                        "Tool IDOR attempt blocked in get_patient_profile",
                        caller_user_id=ctx.user_id,
                        attempted_patient_id=patient_id,
                    )
                    return {
                        "found": False,
                        "error": "Unauthorized: You can only view your own patient profile.",
                    }

            patient = await service.get_patient(
                uuid.UUID(patient_id)
            )

            if patient is None:
                return {
                    "found": False,
                    "error": f"No patient found with ID {patient_id}",
                }

            return {
                "found": True,
                "patient": patient.model_dump(mode="json"),
            }

    except Exception as exc:
        logger.error(
            "get_patient_profile failed",
            patient_id=patient_id,
            error=str(exc),
        )
        return {
            "found": False,
            "error": f"Failed to retrieve patient: {exc}",
        }


@mcp_server.tool()
async def search_patients(query: str) -> dict[str, Any]:
    """
    Search for patients by name, phone number, or email.

    Args:
        query: Search term (partial name, phone, or email).

    Returns:
        List of matching patient profiles.
    """

    from domains.medai.services.patient_service import PatientService

    ctx = get_tool_security_context()

    # Authorization Check: Patients/users cannot search all patients
    if ctx and ctx.role in ("patient", "user"):
        logger.warning(
            "Tool search_patients blocked for non-staff caller",
            caller_user_id=ctx.user_id,
            role=ctx.role,
        )
        return {
            "count": 0,
            "patients": [],
            "error": "Unauthorized: Patients are not permitted to search the patient directory.",
        }

    try:
        async with AsyncSessionLocal() as session:
            service = PatientService(session)

            results = await service.search_patients(query)

            return {
                "count": len(results),
                "patients": [
                    p.model_dump(mode="json") for p in results
                ],
            }

    except Exception as exc:
        logger.error(
            "search_patients failed",
            query=query,
            error=str(exc),
        )
        return {
            "count": 0,
            "patients": [],
            "error": f"Search failed: {exc}",
        }


@mcp_server.tool()
async def get_patient_history(patient_id: str) -> dict[str, Any]:
    """
    Get a patient's complete history including profile data
    and past appointments.

    Args:
        patient_id: The patient's UUID string.

    Returns:
        Combined patient profile and appointment history.
    """

    from domains.medai.services.patient_service import PatientService
    from domains.medai.services.appointment_service import (
        AppointmentService,
    )
    import uuid

    ctx = get_tool_security_context()

    try:
        async with AsyncSessionLocal() as session:
            patient_service = PatientService(session)
            appointment_service = AppointmentService(session)

            # Authorization Check
            if ctx and ctx.role in ("patient", "user"):
                pat_record = await patient_service.get_patient_by_user_id(ctx.user_id, user_email=ctx.email)
                valid_ids = {ctx.user_id}
                if pat_record:
                    valid_ids.add(str(pat_record.id))
                if ctx.patient_id:
                    valid_ids.add(str(ctx.patient_id))

                if str(patient_id) not in valid_ids:
                    logger.warning(
                        "Tool IDOR attempt blocked in get_patient_history",
                        caller_user_id=ctx.user_id,
                        attempted_patient_id=patient_id,
                    )
                    return {
                        "found": False,
                        "error": "Unauthorized: You can only view your own medical history.",
                    }

            pid = uuid.UUID(patient_id)

            # Fetch patient profile
            patient = await patient_service.get_patient(pid)

            if patient is None:
                return {
                    "found": False,
                    "error": f"No patient found with ID {patient_id}",
                }

            # Fetch appointment history
            appointments = await appointment_service.get_by_patient(
                patient_id
            )

            return {
                "found": True,
                "patient": patient.model_dump(mode="json"),
                "appointments": [
                    a.model_dump(mode="json") for a in appointments
                ],
                "total_appointments": len(appointments),
            }

    except Exception as exc:
        logger.error(
            "get_patient_history failed",
            patient_id=patient_id,
            error=str(exc),
        )
        return {
            "found": False,
            "error": f"Failed to retrieve patient history: {exc}",
        }
