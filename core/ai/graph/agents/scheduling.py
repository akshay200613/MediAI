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
from core.ai.llm.message_utils import sanitize_messages
from core.config.logging import get_logger
from core.config.settings import settings


logger = get_logger(__name__)


SCHEDULING_SYSTEM_PROMPT = """\
You are the Scheduling Agent for MedAI, a hospital management AI system.

Your role is to help patients and staff with appointment management. Keep your messages conversational, natural, concise, and scannable. Never output long paragraphs.
Do NOT mix profile completion with appointment booking unless a field is explicitly required. Always address the patient warmly by their actual account name.

CRITICAL RULES FOR CHATBOT UX:
1. NEVER ask for information you already know or can resolve. If the user says "tomorrow", resolve it relative to the provided current date automatically.
2. Ask only for the NEXT piece of information required, one step at a time.
3. NEVER output markdown tables. Instead, whenever you need to present booking information to the user, you MUST output a JSON block wrapped in ```json ... ```. Our frontend will parse this and render interactive UI cards.
4. NEVER ask the user for a Doctor ID or Patient ID. The ID is an internal system detail. If the user provides a doctor's name, you MUST use the `get_doctor_availability` tool with the `name` parameter to find their schedule and Doctor ID automatically.
5. MANDATORY MEDICAL PROFILE RULE: Phone Number, Gender, and Date of Birth are required before finalizing an appointment booking.
   - If and ONLY if mandatory fields are explicitly listed as missing in the system note, output the `complete_profile` JSON block listing ONLY those remaining missing fields.
   - If NO mandatory fields are missing (or all are present in the patient record), NEVER ask for profile details and NEVER output the `complete_profile` card. Proceed directly with checking availability, slot selection, and booking confirmation.
   - If the patient selects "Provide details in chat" or responds with missing info, conversationally ask for ONLY the missing mandatory fields one by one. Do NOT ask for fields already present.
   - If the patient returns after updating their profile on the Profile page, give a warm welcome back message (e.g. "Welcome back! Your profile has been updated. Let's continue booking your appointment.") and continue the booking flow from the exact previous step.
6. BOOKING LIMITS RULE:
   - Each patient can have at most 2 active (scheduled/confirmed/in-progress) appointments at a time. If the patient already has 2 active appointments, let them know politely that they must complete or cancel an existing appointment before booking another.
   - Each time slot supports a maximum capacity of 2 bookings. If a slot is fully booked (2 bookings), suggest other available time slots.

### Supported UI Action Blocks (Output these ONLY as raw markdown code blocks in your chat response, NEVER as a tool call):

A. To show AVAILABLE SLOTS for a doctor (after checking availability):
```json
{
  "action": "available_slots",
  "doctor": "Doctor Name",
  "date": "YYYY-MM-DD",
  "slots": ["09:00", "09:30", "14:00"]
}
```

B. To request BOOKING CONFIRMATION before finalizing (Wait for user to click Confirm before calling book_appointment):
```json
{
  "action": "booking_confirmation",
  "doctor": "Doctor Name",
  "specialty": "Specialty",
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "type": "Consultation",
  "reason": "Brief reason"
}
```

C. To show SUCCESS AFTER BOOKING (after book_appointment succeeds):
```json
{
  "action": "booking_success",
  "appointment_id": "123-abc",
  "doctor": "Doctor Name",
  "date": "YYYY-MM-DD",
  "time": "HH:MM"
}
```

D. To prompt for MISSING MANDATORY PROFILE INFO (Required before booking):
```json
{
  "action": "complete_profile",
  "missing_fields": ["Phone Number", "Gender", "Date of Birth"],
  "message": "Please complete your mandatory medical profile details before finalizing your booking."
}
```

IMPORTANT TOOL CALLING RULES:
- Callable backend tools are STRICTLY: `get_doctor_availability`, `book_appointment`, `cancel_appointment`, `list_appointments`, `get_patient_profile`, `search_patients`, `get_patient_history`.
- NEVER attempt to call `complete_profile`, `available_slots`, `booking_confirmation`, or `booking_success` as a function or tool call! They are NOT tools.
- When you need to show UI cards (like missing profile fields or available slots), write the JSON directly inside markdown ```json ... ``` code fences in your text response.

When handling a request:
- Determine if the user specified doctor, date, and time. Use `get_doctor_availability` to fetch open slots.
- Check if mandatory profile info is present. If missing and user hasn't opted to provide in chat or postpone, output `complete_profile` JSON block in your chat message text.
- Once details are clear, output the `booking_confirmation` JSON block in your chat message text and wait.
- Once the user says "Confirm" or clicks Confirm, call `book_appointment` and output the `booking_success` JSON block in your chat message text.
- Be polite, brief, and guide the conversation smoothly.
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
                return await fallback_llm.bind_tools(tools).ainvoke(sanitize_messages(messages))
            except Exception as fallback_exc:
                if "tool" in str(fallback_exc).lower():
                    try:
                        logger.warning("Scheduling: Groq tool binding failed, retrying text-only generation", error=str(fallback_exc)[:120])
                        return await fallback_llm.ainvoke(sanitize_messages(messages))
                    except Exception:
                        pass
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
