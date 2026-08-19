"""
Knowledge Agent – hospital and policy information specialist.

Responsibilities:

    1. Answer questions about hospital facilities, departments,
       infrastructure, and services
    2. Provide insurance and TPA information
    3. Share contact details, working hours, and location info
    4. Explain hospital policies, procedures, and accreditations

Uses the existing RAG pipeline for grounded retrieval from
the hospital knowledge base.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import BaseMessage

from core.ai.llm.litellm_client import get_llm_client
from core.ai.llm.client import Message
from core.ai.rag.pipeline import RAGPipeline
from core.config.logging import get_logger
from core.config.settings import settings


logger = get_logger(__name__)


KNOWLEDGE_SYSTEM_PROMPT = """\
You are the Knowledge Agent for MedAI, a hospital management AI system.

Your role is to provide accurate information about:
- Hospital facilities, departments, and infrastructure
- Insurance providers, TPA tie-ups, and cashless networks
- Contact numbers, addresses, and working hours
- Accreditations and certifications
- Patient processes (OPD, billing, lab results, first visits)
- Available medical specialties and services
- Hospital group locations

IMPORTANT RULES:
1. Answer ONLY from the provided knowledge base context
2. If information is not available, clearly say:
   "The knowledge base does not contain this information.
   Please contact the hospital helpdesk at 0495 2777 777."
3. Cite sources using [Source N] format when available
4. For insurance-related queries, always include the caveat that
   empanelment lists change frequently and should be verified
5. Provide specific facts, numbers, and named entities
6. Be professional but approachable
"""


class KnowledgeAgent:
    """
    Hospital and policy information specialist.

    Uses the RAG pipeline to retrieve and present information
    from the hospital knowledge base.
    """

    def __init__(self) -> None:
        self.llm = get_llm_client()
        self.rag = RAGPipeline(
            llm_client=self.llm,
            collection_name=(
                f"{settings.qdrant_collection_prefix}_knowledge"
            ),
            system_prompt=KNOWLEDGE_SYSTEM_PROMPT,
        )

    async def process(
        self,
        message: str,
        entities: dict[str, Any] | None = None,
        conversation_history: list[BaseMessage] | None = None,
    ) -> dict[str, Any]:
        """
        Handle a knowledge/information query.

        Args:
            message:
                The user's information question.

            entities:
                Extracted entities (hospital name, topic, etc.).

            conversation_history:
                Prior conversation messages.

        Returns:
            Dict with ``answer``, ``tool_results``,
            and ``requires_handoff``.
        """

        if not message.strip():
            return {
                "answer": (
                    "I can help you with information about our "
                    "hospital facilities, insurance, contact details, "
                    "and more. What would you like to know?"
                ),
                "tool_results": [],
                "requires_handoff": False,
            }

        # Convert LangChain messages to internal format
        history = self._convert_history(conversation_history)

        # ------------------------------------------------------------------
        # Query the RAG pipeline
        # ------------------------------------------------------------------

        try:
            # Build category filter from entities if available
            filters = self._build_filters(entities or {})

            rag_result = await self.rag.query(
                user_query=message,
                conversation_history=history,
                filters=filters,
                model=settings.model_knowledge,
            )

            tool_results = [
                {
                    "tool": "rag_knowledge_query",
                    "retrieved_chunks": rag_result.retrieved_chunks,
                    "sources": rag_result.sources,
                }
            ]

            logger.info(
                "Knowledge agent completed",
                retrieved_chunks=rag_result.retrieved_chunks,
            )

            return {
                "answer": rag_result.answer,
                "tool_results": tool_results,
                "requires_handoff": False,
            }

        except Exception as exc:
            logger.error(
                "Knowledge agent RAG query failed",
                error=str(exc),
            )

            return {
                "answer": (
                    "I'm sorry, I couldn't retrieve that information "
                    "right now. Please contact the hospital helpdesk "
                    "at 0495 2777 777 for assistance."
                ),
                "tool_results": [],
                "requires_handoff": False,
            }

    @staticmethod
    def _build_filters(
        entities: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Build Qdrant filters from extracted entities.

        Maps entity types to Qdrant payload field conditions.
        """

        filters: dict[str, Any] = {}

        # Map entity keys to Qdrant payload fields
        category_map = {
            "insurance": "insurance_tpa",
            "facilities": "facilities",
            "contact": "contact_info",
            "departments": "services_specialties",
            "accreditations": "accreditations",
            "billing": "billing_payment",
        }

        topic = entities.get("topic", "")

        if isinstance(topic, str):
            topic_lower = topic.lower()
            for keyword, category in category_map.items():
                if keyword in topic_lower:
                    filters["category"] = category
                    break

        hospital = entities.get("hospital_name")
        if hospital:
            filters["hospital_name"] = hospital

        return filters if filters else None

    @staticmethod
    def _convert_history(
        messages: list[BaseMessage] | None,
    ) -> list[Message]:
        """Convert LangChain messages to internal Message objects."""

        if not messages:
            return []

        result: list[Message] = []

        for msg in messages:
            role = "user" if msg.type == "human" else "assistant"
            result.append(
                Message(role=role, content=str(msg.content))
            )

        return result
