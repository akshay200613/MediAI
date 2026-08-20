"""
Medical Agent (LangGraph version) – clinical specialist.

Responsibilities:

    1. Symptom triage and clinical decision support
    2. Patient history lookup via MCP patient tools
    3. Medical knowledge retrieval via RAG pipeline
    4. Safety guardrails (emergency flagging, no self-prescribing)

Uses LangChain's bind_tools to autonomously execute tools.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage

from core.ai.llm.litellm_client import get_llm_client, get_fallback_chat_llm, AIServiceUnavailableError
from core.ai.rag.pipeline import RAGPipeline
from core.ai.graph.tools.server import mcp_server
from core.config.logging import get_logger
from core.config.settings import settings


logger = get_logger(__name__)


MEDICAL_SYSTEM_PROMPT = """\
You are the Medical Agent for MedAI, a hospital management AI system.

Your role:
- Help doctors with clinical decision support and patient history summaries
- Help patients understand symptoms and provide evidence-based guidance
- Triage symptom severity and recommend appropriate action

CRITICAL SAFETY RULES:
1. NEVER prescribe medications — only doctors can prescribe
2. ALWAYS recommend consulting a qualified doctor for diagnosis
3. FLAG emergency symptoms IMMEDIATELY:
   - Chest pain or pressure
   - Difficulty breathing
   - Severe bleeding
   - Loss of consciousness
   - Signs of stroke (FAST: Face, Arms, Speech, Time)
   - Severe allergic reaction (anaphylaxis)
4. Maintain patient confidentiality at all times
5. Be empathetic, clear, and professional

When providing medical information:
- Use your tools to retrieve context from the knowledge base or patient records
- Cite sources when available using [Source N] format
- Clearly distinguish between general medical information and patient-specific advice
- If information is insufficient, say so clearly
"""


class MedicalGraphAgent:
    """
    LangGraph-native medical agent.

    Uses ChatLiteLLM bound with FastMCP tools
    (including the knowledge base tool) for autonomous tool calling.
    Falls back to Groq explicitly on Gemini rate-limit / quota errors.
    """

    _RATE_LIMIT_SIGNALS = (
        "RateLimitError", "ResourceExhausted", "RESOURCE_EXHAUSTED",
        "quota", "429", "rate limit", "rate_limit",
    )

    def __init__(self) -> None:
        self._primary_model = settings.model_medical
        self._fallback_model = settings.model_fallback_medical
        self._temperature = 1.0
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
                "Medical: Gemini rate-limited – switching to Groq fallback",
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
                    "Medical: Groq fallback also failed",
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
        Handle a medical query using autonomous tool calling.
        """

        if not message.strip():
            return {
                "answer": "Please describe your medical concern.",
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
            
            med_info = patient_context.get("medical_info", {})
            if med_info:
                context_parts.append(f"Allergies: {', '.join(med_info.get('allergies', []))}")
                context_parts.append(f"Chronic Conditions: {', '.join(med_info.get('chronic_conditions', []))}")
                context_parts.append(f"Current Medications: {', '.join(med_info.get('current_medications', []))}")
            context_parts.append("-----------------------")

        prompt = "\n".join(context_parts)

        # ------------------------------------------------------------------
        # Generate response using tool binding
        # ------------------------------------------------------------------

        try:
            # Get LangChain compatible tools from FastMCP server
            all_tools = await mcp_server.list_tools()
            
            # Tools appropriate for the medical agent
            medical_tool_names = {
                "get_patient_profile", "get_patient_history",
                "query_knowledge_base"
            }
            tools = [t.fn for t in all_tools if t.name in medical_tool_names and hasattr(t, "fn")]

            messages = [SystemMessage(content=MEDICAL_SYSTEM_PROMPT)]
            if conversation_history:
                messages.extend(conversation_history)
            messages.append(HumanMessage(content=prompt))

            response = await self._invoke_with_fallback(self.llm, tools, messages)

            # Check if scheduling handoff is needed
            needs_scheduling = self._check_scheduling_need(message, entities)

            logger.info(
                "Medical agent completed",
                requires_handoff=needs_scheduling,
                tool_calls=len(response.tool_calls) if hasattr(response, 'tool_calls') else 0,
            )

            return {
                "message": response,
                "requires_handoff": needs_scheduling,
            }

        except AIServiceUnavailableError:
            raise
        except Exception as exc:
            logger.error(
                "Medical agent failed",
                error=str(exc),
            )

            return {
                "answer": (
                    "I'm sorry, I encountered an issue processing "
                    "your medical request."
                ),
                "requires_handoff": False,
            }

    @staticmethod
    def _check_scheduling_need(
        message: str,
        entities: dict[str, Any],
    ) -> bool:
        """Heuristic check for scheduling handoff."""

        scheduling_keywords = {
            "book", "appointment", "schedule", "available", 
            "slot", "reschedule", "cancel",
        }

        message_lower = message.lower()
        if any(kw in message_lower for kw in scheduling_keywords):
            return True
        if entities.get("date") or entities.get("doctor_name"):
            return True
        return False
