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

    try:
        async with AsyncSessionLocal() as session:
            service = PatientService(session)

            import uuid
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

    try:
        async with AsyncSessionLocal() as session:
            patient_service = PatientService(session)
            appointment_service = AppointmentService(session)

            import uuid
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
