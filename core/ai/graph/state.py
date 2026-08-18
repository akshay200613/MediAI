"""
MedAI Graph State – the shared state that flows through every node.

This TypedDict defines the complete data contract for the
LangGraph state machine. Every node reads from and writes to
this structure.

State flow:

    User message
        ↓
    ReceptionNode  →  classifies intent, extracts entities
        ↓
    SupervisorNode →  routes to specialist
        ↓
    SpecialistNode →  produces answer + tool_results
        ↓
    ResponseNode   →  formats final output
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


# ============================================================================
# Intent categories recognized by the reception agent
# ============================================================================

IntentType = Literal[
    "medical",
    "scheduling",
    "knowledge",
    "general",
]


# ============================================================================
# Graph state
# ============================================================================


class MedAIState(TypedDict):
    """
    Shared state for the MedAI LangGraph state machine.

    Attributes:
        messages:
            Full conversation history. Uses LangGraph's built-in
            ``add_messages`` reducer so each node can simply
            return new messages and they get appended automatically.

        user_id:
            Authenticated user's UUID (from JWT).

        session_id:
            Conversation session identifier (maps to Redis
            session history).

        intent:
            Classified intent produced by the reception agent.
            Determines which specialist the supervisor routes to.

        entities:
            Named entities extracted by the reception agent
            (patient name, date, symptom, doctor name, etc.).

        current_agent:
            Name of the specialist agent currently handling
            the request. Set by the supervisor.

        tool_results:
            Results returned by MCP tool calls. Specialist
            agents populate this after invoking tools.

        requires_handoff:
            Flag indicating the specialist needs the supervisor
            to re-route to a different agent (e.g. a medical
            query that also requires scheduling).

        final_response:
            The formatted answer to return to the user.
            Populated by the response node.

        metadata:
            Extensible bag for domain-specific data that
            doesn't fit the other fields.
    """

    # Conversation
    messages: Annotated[list[BaseMessage], add_messages]

    # Identity
    user_id: str
    session_id: str

    # Intent classification
    intent: IntentType | None
    entities: dict[str, Any]

    # Patient context
    patient_context: dict[str, Any]

    # Routing
    current_agent: str

    # Tool layer
    tool_results: list[dict[str, Any]]

    # Control flow
    requires_handoff: bool
    final_response: str

    # Extension point
    metadata: dict[str, Any]
