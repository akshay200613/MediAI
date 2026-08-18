"""
Scheduling Agent – appointment specialist for the MedAI graph.

Responsibilities:

    1. Book new appointments
    2. Reschedule existing appointments
    3. Cancel appointments
    4. Check doctor availability
    5. List upcoming appointments for a patient

Uses appointment_tools and patient_tools via MCP for
database operations. Uses LangChain's bind_tools to
autonomously execute tools.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from core.ai.graph.tools.server import mcp_server
from core.config.logging import get_logger
from core.config.settings import settings


logger = get_logger(__name__)


SCHEDULING_SYSTEM_PROMPT = """\
You are the Scheduling Agent for MedAI, a hospital management AI system.

Your role is to help patients and staff with appointment management:
- Book new appointments
- Reschedule existing appointments
- Cancel appointments
- Check doctor availability
- Show upcoming appointments

When handling appointment requests:
1. Confirm all required details before booking:
   - Patient identity (name or ID)
   - Doctor or specialty preference
   - Preferred date and time
   - Appointment type (consultation, follow-up, emergency, etc.)
   - Reason for visit (brief)

2. If any required information is missing, ask the user politely.

3. For cancellations, confirm the appointment details before proceeding.

4. Present doctor availability clearly with time slots.

5. After booking, provide a confirmation summary with:
   - Appointment ID
   - Doctor name
   - Date/time
   - Location/department

Use your tools to query patient info, doctor availability, and manage appointments.
Always be polite, efficient, and confirm actions before executing them.
"""


class SchedulingAgent:
    """
    Handles appointment booking, rescheduling, and cancellation.

    Uses LangChain and FastMCP tools for autonomous execution.
    """

    def __init__(self) -> None:
        self.llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=0.0,
        )

    async def process(
        self,
        message: str,
        entities: dict[str, Any] | None = None,
        conversation_history: list[BaseMessage] | None = None,
        user_id: str = "",
        patient_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Handle a scheduling request using autonomous tool calling.
        """

        if not message.strip():
            return {
                "answer": (
                    "I can help you with appointment scheduling. "
                    "Would you like to book, reschedule, or cancel "
                    "an appointment?"
                ),
                "tool_results": [],
                "requires_handoff": False,
            }

        entities = entities or {}

        # ------------------------------------------------------------------
        # Build context-aware prompt
        # ------------------------------------------------------------------

        context_parts = [
            f"User request: {message}",
            f"Extracted entities: {entities}",
            f"User ID: {user_id}",
        ]
        
        if patient_context:
            context_parts.append("\n--- PATIENT CONTEXT ---")
            context_parts.append(f"Name: {patient_context.get('first_name')} {patient_context.get('last_name')}")
            context_parts.append(f"Date of Birth: {patient_context.get('date_of_birth')}")
            context_parts.append(f"Blood Group: {patient_context.get('blood_group')}")
            context_parts.append("-----------------------")

        prompt = "\n".join(context_parts)

        # ------------------------------------------------------------------
        # Generate response using tool binding
        # ------------------------------------------------------------------

        try:
            # Get LangChain compatible tools from FastMCP server
            # We want patient and appointment tools
            all_tools = await mcp_server.get_tools()
            
            # Filter tools meant for scheduling
            scheduling_tool_names = {
                "get_patient_profile", "search_patients", "get_patient_history",
                "list_appointments", "book_appointment", "cancel_appointment", 
                "get_doctor_availability"
            }
            tools = [t for t in all_tools if t.name in scheduling_tool_names]

            llm_with_tools = self.llm.bind_tools(tools)

            messages = [SystemMessage(content=SCHEDULING_SYSTEM_PROMPT)]
            if conversation_history:
                messages.extend(conversation_history)
            messages.append(HumanMessage(content=prompt))

            response = await llm_with_tools.ainvoke(messages)

            # Check if medical handoff is needed
            needs_medical = self._check_medical_need(message, entities)

            logger.info(
                "Scheduling agent completed",
                requires_handoff=needs_medical,
                tool_calls=len(response.tool_calls) if hasattr(response, 'tool_calls') else 0,
            )

            # Return the raw AIMessage so the graph can process tool calls
            return {
                "message": response,
                "requires_handoff": needs_medical,
            }

        except Exception as exc:
            logger.error(
                "Scheduling agent failed",
                error=str(exc),
            )

            return {
                "answer": (
                    "I'm sorry, I encountered an issue processing "
                    "your scheduling request. Please try again or "
                    "call the hospital reception at 0495 2777 777."
                ),
                "requires_handoff": False,
            }

    @staticmethod
    def _check_medical_need(
        message: str,
        entities: dict[str, Any],
    ) -> bool:
        """Check if the message also has a medical component."""

        medical_keywords = {
            "symptom", "pain", "fever", "diagnosis", "treatment",
            "medication", "bleeding", "emergency",
        }

        message_lower = message.lower()
        if any(kw in message_lower for kw in medical_keywords):
            return True
        if entities.get("symptoms"):
            return True
        return False
