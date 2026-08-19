"""
Database / Knowledge Tools – MCP-compatible tools for data queries.

Wraps the RAG pipeline and domain services to provide
knowledge base access and structured database queries
to LangGraph agents.

Tools:

    query_knowledge_base → RAG-powered knowledge base search
    get_hospital_info    → Structured hospital data lookup
    search_doctors       → Doctor directory search by specialty/name
"""

from __future__ import annotations

from typing import Any

from core.ai.graph.tools.server import mcp_server
from core.config.logging import get_logger


logger = get_logger(__name__)


@mcp_server.tool()
async def query_knowledge_base(question: str) -> dict[str, Any]:
    """
    Query the hospital knowledge base using RAG retrieval.

    Uses hybrid retrieval (dense + sparse) with reranking
    to find the most relevant information.

    Args:
        question: The question to search for in the knowledge base.

    Returns:
        Answer from the knowledge base with source citations.
    """

    from core.ai.llm.litellm_client import get_llm_client
    from core.ai.rag.pipeline import RAGPipeline
    from core.config.settings import settings

    try:
        llm = get_llm_client()

        rag = RAGPipeline(
            llm_client=llm,
            collection_name=(
                f"{settings.qdrant_collection_prefix}_knowledge"
            ),
        )

        result = await rag.query(user_query=question)

        return {
            "answer": result.answer,
            "retrieved_chunks": result.retrieved_chunks,
            "sources": result.sources,
        }

    except Exception as exc:
        logger.error(
            "query_knowledge_base failed",
            question=question,
            error=str(exc),
        )
        return {
            "answer": "",
            "retrieved_chunks": 0,
            "sources": [],
            "error": f"Knowledge base query failed: {exc}",
        }


@mcp_server.tool()
async def get_hospital_info(topic: str) -> dict[str, Any]:
    """
    Get structured hospital information by topic.

    Performs a targeted RAG query filtered by category
    for more precise results.

    Args:
        topic: Information topic. Supported topics:
               - "contact": phone numbers, address, email
               - "facilities": infrastructure, equipment, beds
               - "insurance": insurance providers, TPA tie-ups
               - "specialties": medical departments, services
               - "accreditations": certifications, awards
               - "appointments": OPD process, booking channels
               - "billing": payment methods, billing process
               - "locations": hospital group locations

    Returns:
        Targeted information about the requested topic.
    """

    from core.ai.llm.litellm_client import get_llm_client
    from core.ai.rag.pipeline import RAGPipeline
    from core.config.settings import settings

    # Map topics to knowledge base categories
    topic_to_category = {
        "contact": "contact_info",
        "facilities": "facilities",
        "infrastructure": "facilities",
        "insurance": "insurance_tpa",
        "tpa": "insurance_tpa",
        "specialties": "services_specialties",
        "departments": "services_specialties",
        "services": "services_specialties",
        "accreditations": "accreditations",
        "awards": "accreditations",
        "appointments": "patient_process_outpatient",
        "opd": "patient_process_outpatient",
        "booking": "patient_process_outpatient",
        "billing": "billing_payment",
        "payment": "billing_payment",
        "locations": "general_info",
        "branches": "general_info",
    }

    try:
        llm = get_llm_client()

        rag = RAGPipeline(
            llm_client=llm,
            collection_name=(
                f"{settings.qdrant_collection_prefix}_knowledge"
            ),
        )

        # Build targeted query
        query = f"What is the {topic} information for the hospital?"

        # Build category filter
        category = topic_to_category.get(
            topic.lower().strip(), None
        )
        filters = {"category": category} if category else None

        result = await rag.query(
            user_query=query,
            filters=filters,
        )

        return {
            "topic": topic,
            "answer": result.answer,
            "retrieved_chunks": result.retrieved_chunks,
            "sources": result.sources,
        }

    except Exception as exc:
        logger.error(
            "get_hospital_info failed",
            topic=topic,
            error=str(exc),
        )
        return {
            "topic": topic,
            "answer": "",
            "retrieved_chunks": 0,
            "sources": [],
            "error": f"Hospital info query failed: {exc}",
        }


@mcp_server.tool()
async def search_doctors(
    specialty: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """
    Search the doctor directory by specialty or name.

    Args:
        specialty: Medical specialty to filter by
                   (e.g., "cardiology", "neurology").
        name: Doctor's name to search for (partial match).

    Returns:
        List of matching doctors with their details.
    """

    from domains.medai.services.doctor_service import DoctorService
    from core.database.base import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as session:
            service = DoctorService(session)

            if name:
                doctors = await service.search_doctors(name)
            elif specialty:
                doctors = await service.get_available_doctors(
                    specialty
                )
            else:
                result = await service.list_doctors(
                    page=1, page_size=20
                )
                doctors = result.data

            return {
                "count": len(doctors),
                "doctors": [
                    d.model_dump(mode="json") for d in doctors
                ],
            }

    except Exception as exc:
        logger.error(
            "search_doctors failed",
            specialty=specialty,
            name=name,
            error=str(exc),
        )
        return {
            "count": 0,
            "doctors": [],
            "error": f"Doctor search failed: {exc}",
        }
