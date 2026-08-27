"""
Graph node functions for the MedAI LangGraph.

Each function is a thin wrapper that:

    1. Reads the shared ``MedAIState``
    2. Delegates to the corresponding agent class
    3. Returns state updates

Node pipeline:

    reception_node  →  intent + entities
    supervisor_node →  current_agent routing decision
    medical_node    →  clinical answer
    scheduling_node →  appointment action
    knowledge_node  →  hospital/policy answer
    response_node   →  formatted final output
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from core.ai.graph.agents.knowledge import KnowledgeAgent
from core.ai.graph.agents.medical import MedicalGraphAgent
from core.ai.graph.agents.reception import ReceptionAgent
from core.ai.graph.agents.scheduling import SchedulingAgent
from core.ai.graph.agents.supervisor import SupervisorAgent
from core.ai.graph.state import MedAIState
from core.ai.graph.tools.server import mcp_server
from core.ai.llm.litellm_client import AIServiceUnavailableError  # noqa: F401 – re-exported for graph callers
from core.ai.llm.message_utils import sanitize_messages
from langgraph.prebuilt import ToolNode
from core.config.logging import get_logger


logger = get_logger(__name__)


# ============================================================================
# Singleton agent instances (created lazily)
# ============================================================================

_reception: ReceptionAgent | None = None
_supervisor: SupervisorAgent | None = None
_medical: MedicalGraphAgent | None = None
_scheduling: SchedulingAgent | None = None
_knowledge: KnowledgeAgent | None = None


def _get_reception() -> ReceptionAgent:
    global _reception
    if _reception is None:
        _reception = ReceptionAgent()
    return _reception


def _get_supervisor() -> SupervisorAgent:
    global _supervisor
    if _supervisor is None:
        _supervisor = SupervisorAgent()
    return _supervisor


def _get_medical() -> MedicalGraphAgent:
    global _medical
    if _medical is None:
        _medical = MedicalGraphAgent()
    return _medical


def _get_scheduling() -> SchedulingAgent:
    global _scheduling
    if _scheduling is None:
        _scheduling = SchedulingAgent()
    return _scheduling


def _get_knowledge() -> KnowledgeAgent:
    global _knowledge
    if _knowledge is None:
        _knowledge = KnowledgeAgent()
    return _knowledge


# ============================================================================
# Node functions
# ============================================================================


async def reception_node(state: MedAIState) -> dict:
    """
    First contact – classify intent and extract entities.

    Reads the latest user message and produces:

        - ``intent``: medical | scheduling | knowledge | general
        - ``entities``: extracted named entities
    """

    agent = _get_reception()

    last_message = _get_last_user_text(state)

    result = await agent.process(
        message=last_message,
        conversation_history=sanitize_messages(state.get("messages", [])),
    )

    logger.info(
        "Reception classified intent",
        intent=result["intent"],
        entities=result.get("entities", {}),
    )

    patient_context = state.get("patient_context", {})

    # If we have a user_id and haven't fetched the context yet
    if state.get("user_id") and not patient_context:
        try:
            from core.ai.graph.tools.patient_tools import get_patient_profile
            # FastMCP decorated tools can be called directly
            profile_response = await get_patient_profile(state["user_id"])
            if profile_response.get("found"):
                patient_context = profile_response.get("patient", {})
        except Exception as exc:
            logger.error("Failed to fetch patient context", error=str(exc))

    return {
        "intent": result["intent"],
        "entities": result.get("entities", {}),
        "patient_context": patient_context,
    }


async def supervisor_node(state: MedAIState) -> dict:
    """
    Routing brain – validate intent and select specialist.

    May override the reception's classification if context
    suggests a different specialist is needed.
    """

    agent = _get_supervisor()

    result = await agent.process(
        intent=state.get("intent", "general"),
        entities=state.get("entities", {}),
        conversation_history=sanitize_messages(state.get("messages", [])),
    )

    logger.info(
        "Supervisor routed to agent",
        current_agent=result["current_agent"],
        intent=result.get("intent", state.get("intent")),
    )

    return {
        "current_agent": result["current_agent"],
        "intent": result.get("intent", state.get("intent")),
        "requires_handoff": False,
    }


async def medical_node(state: MedAIState) -> dict:
    """
    Clinical specialist – handles medical queries.

    Uses the RAG pipeline for grounded medical knowledge
    and patient tools for history lookup.

    Raises ``AIServiceUnavailableError`` when both Gemini and Groq fail
    so the chat endpoint can return a proper 503.
    """

    agent = _get_medical()

    last_message = _get_last_user_text(state)

    result = await agent.process(
        message=last_message,
        entities=state.get("entities", {}),
        conversation_history=sanitize_messages(state.get("messages", [])),
        user_id=state.get("user_id", ""),
        patient_context=state.get("patient_context", {}),
    )

    if "message" in result:
        messages_update = [result["message"]]
    else:
        messages_update = [AIMessage(content=result.get("answer", ""))]

    return {
        "messages": messages_update,
        "requires_handoff": result.get("requires_handoff", False),
    }


async def scheduling_node(state: MedAIState) -> dict:
    """
    Appointment specialist – books, reschedules, cancels.

    Uses appointment tools and patient tools via MCP.

    Raises ``AIServiceUnavailableError`` when both Gemini and Groq fail
    so the chat endpoint can return a proper 503.
    """

    agent = _get_scheduling()

    last_message = _get_last_user_text(state)

    result = await agent.process(
        message=last_message,
        entities=state.get("entities", {}),
        conversation_history=sanitize_messages(state.get("messages", [])),
        user_id=state.get("user_id", ""),
        patient_context=state.get("patient_context", {}),
    )

    if "message" in result:
        messages_update = [result["message"]]
    else:
        messages_update = [AIMessage(content=result.get("answer", ""))]

    return {
        "messages": messages_update,
        "requires_handoff": result.get("requires_handoff", False),
    }


async def knowledge_node(state: MedAIState) -> dict:
    """
    Hospital/policy information specialist.

    Answers questions about facilities, insurance, contact
    info, and operational policies using the RAG pipeline
    and database tools.

    Raises ``AIServiceUnavailableError`` when both Gemini and Groq fail
    so the chat endpoint can return a proper 503.
    """

    agent = _get_knowledge()

    last_message = _get_last_user_text(state)

    result = await agent.process(
        message=last_message,
        entities=state.get("entities", {}),
        conversation_history=sanitize_messages(state.get("messages", [])),
    )

    return {
        "messages": [AIMessage(content=result["answer"])],
        "tool_results": result.get("tool_results", []),
        "requires_handoff": result.get("requires_handoff", False),
    }


async def response_node(state: MedAIState) -> dict:
    """
    Terminal node – formats the final response.

    For ``general`` intent (no specialist needed), generates
    a direct conversational response. Otherwise, passes through
    the specialist's answer.
    """

    messages = state.get("messages", [])

    # If a specialist already produced an AI message, use it.
    if messages:
        last = messages[-1]

        if isinstance(last, AIMessage) and last.content:
            return {"final_response": last.content}

    # Fallback for general intent – produce a helpful reply.
    return {
        "final_response": (
            "I'm sorry, but I didn't quite understand that. "
            "I'm MedAI, your intelligent clinic assistant, and I can help you with medical questions, "
            "appointment scheduling, and hospital information. Could you please rephrase your question?"
        ),
    }


_tool_node_instance: ToolNode | None = None


async def mcp_tool_node(state: MedAIState) -> dict:
    """
    Executes tool calls requested by the agents.
    Lazily initializes the LangGraph ToolNode with FastMCP tools.
    """
    global _tool_node_instance
    if _tool_node_instance is None:
        all_tools = await mcp_server.list_tools()
        tools = [t.fn for t in all_tools if hasattr(t, "fn")]
        _tool_node_instance = ToolNode(tools)

    # ToolNode returns {"messages": [ToolMessage(...)]}
    return await _tool_node_instance.ainvoke(state)


# ============================================================================
# Helpers
# ============================================================================


def _get_last_user_text(state: MedAIState) -> str:
    """Extract the text of the most recent user message."""

    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return str(message.content)

    return ""
