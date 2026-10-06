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

from core.ai.llm.litellm_client import (
    get_llm_client,
    get_fallback_chat_llm,
    AIServiceUnavailableError,
    normalize_model_name,
    get_model_api_key,
)
from core.ai.llm.message_utils import sanitize_messages
from core.ai.rag.pipeline import RAGPipeline
from core.ai.graph.tools.server import mcp_server
from core.config.logging import get_logger
from core.config.settings import settings


logger = get_logger(__name__)


import yaml
from pathlib import Path

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "medical.yaml"
with open(_PROMPT_PATH, "r", encoding="utf-8") as _f:
    MEDICAL_SYSTEM_PROMPT = yaml.safe_load(_f)["system_prompt"]


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
        """Invoke the LLM. On any primary failure (503 high demand, 429 rate limit, timeouts), retry with fallback model."""
        try:
            return await llm.bind_tools(tools).ainvoke(messages)
        except AIServiceUnavailableError:
            raise
        except Exception as primary_exc:
            logger.warning(
                "Medical: Primary model failed – switching to fallback",
                fallback=self._fallback_model,
                error=str(primary_exc)[:160],
            )

            if not self._fallback_model:
                raise AIServiceUnavailableError(
                    AIServiceUnavailableError.USER_MESSAGE
                ) from primary_exc

            norm_fallback = normalize_model_name(self._fallback_model)
            api_key = get_model_api_key(norm_fallback)
            if not api_key:
                raise AIServiceUnavailableError(
                    AIServiceUnavailableError.USER_MESSAGE
                ) from primary_exc

            fallback_llm = self._make_llm(norm_fallback, api_key)
            try:
                return await fallback_llm.bind_tools(tools).ainvoke(sanitize_messages(messages))
            except Exception as fallback_exc:
                if "tool" in str(fallback_exc).lower():
                    try:
                        logger.warning("Medical: Fallback tool binding failed, retrying text-only generation", error=str(fallback_exc)[:120])
                        return await fallback_llm.ainvoke(sanitize_messages(messages))
                    except Exception:
                        pass
                logger.error(
                    "Medical: Fallback also failed",
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
            logger.warning("Medical agent hit rate limit / AIServiceUnavailableError")
            return {
                "answer": (
                    "I'm sorry, our AI service is currently hitting rate limits and experiencing high traffic. "
                    "Please try again in a moment."
                ),
                "requires_handoff": False,
            }
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
