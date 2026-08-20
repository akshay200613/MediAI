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

from core.ai.graph.tools.server import mcp_server
from core.ai.llm.litellm_client import get_fallback_chat_llm, AIServiceUnavailableError
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

CRITICAL RULE:
You MUST NOT call the `book_appointment` tool if the preferred date and time are not specified by the user. Do not guess or assume a date and time. If the date and/or time is missing, you must:
1. Check the doctor's availability first using `get_doctor_availability` to find suitable slots.
2. Ask the user politely to specify their preferred date and time.
3. Only proceed with booking once they provide a specific date and time.

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

5. NEVER ask the user for a Doctor ID or Patient ID. The ID is an internal system detail. If the user provides a doctor's name, you MUST use the `get_doctor_availability` tool with the `name` parameter to find their schedule and Doctor ID automatically.

6. After booking, provide a confirmation summary with:
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
    Falls back to Groq explicitly on Gemini rate-limit / quota errors.
    """

    _RATE_LIMIT_SIGNALS = (
        "RateLimitError", "ResourceExhausted", "RESOURCE_EXHAUSTED",
        "quota", "429", "rate limit", "rate_limit",
    )

    def __init__(self) -> None:
        self._primary_model = settings.model_scheduling
        self._fallback_model = settings.model_fallback_scheduling
        self._temperature = 1.0
        # Primary ChatLiteLLM (Gemini)
        self.llm = self._make_llm(self._primary_model, settings.gemini_api_key)

    def _make_llm(self, model: str, api_key: str):
        from langchain_litellm import ChatLiteLLM
        return ChatLiteLLM(model=model, temperature=self._temperature, api_key=api_key)

    def _is_rate_limit(self, exc: Exception) -> bool:
        exc_str = str(exc)
        return any(signal in exc_str for signal in self._RATE_LIMIT_SIGNALS)

    async def _invoke_with_fallback(self, llm, tools, messages):
        """Invoke the LLM. On Gemini rate-limit, transparently retry with Groq."""
        try:
            return await llm.bind_tools(tools).ainvoke(messages)
        except AIServiceUnavailableError:
            raise
        except Exception as primary_exc:
            if not self._is_rate_limit(primary_exc):
                raise

            logger.warning(
                "Scheduling: Gemini rate-limited – switching to Groq fallback",
                fallback=self._fallback_model,
                error=str(primary_exc)[:120],
            )

            if not self._fallback_model or not settings.groq_api_key:
                raise AIServiceUnavailableError(
                    AIServiceUnavailableError.USER_MESSAGE
                ) from primary_exc

            fallback_llm = self._make_llm(self._fallback_model, settings.groq_api_key)
            try:
                return await fallback_llm.bind_tools(tools).ainvoke(messages)
            except Exception as fallback_exc:
                logger.error(
                    "Scheduling: Groq fallback also failed",
                    error=str(fallback_exc)[:120],
                )
                raise AIServiceUnavailableError(
                    AIServiceUnavailableError.USER_MESSAGE
                ) from fallback_exc

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
            context_parts.append(f"Patient ID: {patient_context.get('patient_id')}")
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
            all_tools = await mcp_server.list_tools()
            
            # Check if we have a date/time indicator in the query or conversation history
            has_date_time = False
            search_text = message.lower()
            if conversation_history:
                search_text += " " + " ".join([
                    m.content.lower() for m in conversation_history 
                    if hasattr(m, 'content') and isinstance(m.content, str)
                ])
            
            import re
            date_time_indicators = [
                r"\b\d{4}-\d{2}-\d{2}\b",  # YYYY-MM-DD
                r"\b\d{1,2}:\d{2}\b",      # HH:MM
                r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
                r"\b(tomorrow|today|next week|morning|afternoon|pm|am)\b",
                r"\b\d{1,2}(st|nd|rd|th)\b",  # 1st, 2nd, etc.
                r"\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b"
            ]
            if any(re.search(pattern, search_text) for pattern in date_time_indicators):
                has_date_time = True

            # Filter tools meant for scheduling
            scheduling_tool_names = {
                "get_patient_profile", "search_patients", "get_patient_history",
                "list_appointments", "cancel_appointment", 
                "get_doctor_availability"
            }
            if has_date_time:
                scheduling_tool_names.add("book_appointment")
                
            tools = [t.fn for t in all_tools if t.name in scheduling_tool_names and hasattr(t, "fn")]

            messages = [SystemMessage(content=SCHEDULING_SYSTEM_PROMPT)]
            if conversation_history:
                messages.extend(conversation_history)
            messages.append(HumanMessage(content=prompt))

            response = await self._invoke_with_fallback(self.llm, tools, messages)

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

        except AIServiceUnavailableError:
            raise
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
