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
        ├─ requires_handoff=True  → supervisor_node
        └─ requires_handoff=False → response_node
"""

from __future__ import annotations

from core.ai.graph.state import MedAIState


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


from langchain_core.messages import AIMessage

def should_continue(state: MedAIState) -> str:
    """
    After a specialist finishes, decide whether to hand back
    to the supervisor, execute tools, or proceed to the response node.
    """
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
