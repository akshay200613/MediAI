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
from langchain_google_genai import ChatGoogleGenerativeAI

from core.ai.llm.gemini_client import get_llm_client
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

    Uses ChatGoogleGenerativeAI bound with FastMCP tools
    (including the knowledge base tool) for autonomous tool calling.
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

            llm_with_tools = self.llm.bind_tools(tools)

            messages = [SystemMessage(content=MEDICAL_SYSTEM_PROMPT)]
            if conversation_history:
                messages.extend(conversation_history)
            messages.append(HumanMessage(content=prompt))

            response = await llm_with_tools.ainvoke(messages)

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
