"""
Conditional edge functions for the MedAI LangGraph.

These functions inspect the current graph state and return
the name of the next node to execute.

Edge map:

    supervisor_node
        │
        ├─ "medical"    → medical_node
        ├─ "scheduling" → scheduling_node
        ├─ "knowledge"  → knowledge_node
        └─ "general"    → response_node

    specialist_node
        │
        ├─ tool_calls pending + under limit → mcp_tool_node
        ├─ requires_handoff=True           → supervisor_node
        └─ otherwise                       → response_node
"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from core.ai.graph.state import MedAIState


# Maximum number of tool-call rounds per conversation turn.
# Prevents runaway mcp_tool_node → specialist loops.
MAX_TOOL_CALLS: int = 8


def route_by_intent(state: MedAIState) -> str:
    """
    Route from the supervisor to the appropriate specialist.

    Reads ``state["intent"]`` set by the reception agent and
    validated by the supervisor.

    Returns:
        Name of the next graph node.
    """

    intent = state.get("intent")

    intent_to_node = {
        "medical": "medical_node",
        "scheduling": "scheduling_node",
        "knowledge": "knowledge_node",
        "general": "response_node",
    }

    return intent_to_node.get(intent or "general", "response_node")


def should_continue(state: MedAIState) -> str:
    """
    After a specialist finishes, decide whether to execute tools,
    hand back to the supervisor, or proceed to the response node.

    Circuit-breaker: if tool_call_count >= MAX_TOOL_CALLS, skip
    any pending tool calls and route directly to response_node to
    prevent infinite tool-execution loops.
    """
    # ── Circuit-breaker check ─────────────────────────────────────────────────
    tool_call_count = state.get("tool_call_count", 0)
    if tool_call_count >= MAX_TOOL_CALLS:
        from core.config.logging import get_logger
        get_logger(__name__).warning(
            "Tool call circuit-breaker triggered; forcing response_node",
            tool_call_count=tool_call_count,
            max_allowed=MAX_TOOL_CALLS,
        )
        return "response_node"

    # ── Normal routing ────────────────────────────────────────────────────────
    messages = state.get("messages", [])
    if messages:
        last_message = messages[-1]
        if isinstance(last_message, AIMessage) and getattr(last_message, "tool_calls", None):
            return "mcp_tool_node"

    if state.get("requires_handoff", False):
        return "supervisor_node"

    return "response_node"


def route_after_tool(state: MedAIState) -> str:
    """
    Return to the active specialist after a tool call completes.
    """
    return state.get("current_agent", "response_node")
