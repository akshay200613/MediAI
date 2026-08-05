"""
LangGraph Base State – TypedDict shared across all agent graphs.
Domain workflows extend this with domain-specific fields.
"""

from typing import Annotated, Any
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Base state for all LangGraph agent graphs.

    `messages` uses the add_messages reducer to accumulate
    messages across graph nodes.
    """
    messages: Annotated[list, add_messages]
    session_id: str
    user_id: str
    domain: str
    context: dict[str, Any]  # domain-specific context
    tool_calls: list[dict]
    sources: list[dict]       # RAG sources
    error: str | None
    is_complete: bool
