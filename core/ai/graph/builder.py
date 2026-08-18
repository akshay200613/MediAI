"""
MedAI Graph Builder – constructs the LangGraph StateGraph.

Topology:

    START
      ↓
    reception_node
      ↓
    supervisor_node
      ↓ (conditional: route_by_intent)
      ├─ medical_node    ──→ (conditional: should_continue)
      ├─ scheduling_node ──→ (conditional: should_continue)
      ├─ knowledge_node  ──→ (conditional: should_continue)
      └─ response_node   ──→ END
                               ↑
                    should_continue may loop back
                    to supervisor_node for multi-step

Usage:

    from core.ai.graph import build_medai_graph

    graph = build_medai_graph()
    result = await graph.ainvoke({
        "messages": [HumanMessage(content="...")],
        "user_id": "...",
        "session_id": "...",
    })
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from core.ai.graph.edges import route_by_intent, should_continue, route_after_tool
from core.ai.graph.nodes import (
    knowledge_node,
    medical_node,
    reception_node,
    response_node,
    scheduling_node,
    supervisor_node,
    mcp_tool_node,
)
from core.ai.graph.state import MedAIState
from core.config.logging import get_logger
from core.config.settings import settings


logger = get_logger(__name__)


def build_medai_graph() -> StateGraph:
    """
    Build and compile the MedAI multi-agent graph.

    Returns:
        A compiled LangGraph ``CompiledStateGraph`` ready
        for ``ainvoke()`` or ``astream()``.
    """

    graph = StateGraph(MedAIState)

    # ==================================================================
    # Register nodes
    # ==================================================================

    graph.add_node("reception_node", reception_node)
    graph.add_node("supervisor_node", supervisor_node)
    graph.add_node("medical_node", medical_node)
    graph.add_node("scheduling_node", scheduling_node)
    graph.add_node("knowledge_node", knowledge_node)
    graph.add_node("response_node", response_node)
    graph.add_node("mcp_tool_node", mcp_tool_node)

    # ==================================================================
    # Entry point
    # ==================================================================

    graph.set_entry_point("reception_node")

    # ==================================================================
    # Edges: reception → supervisor (always)
    # ==================================================================

    graph.add_edge("reception_node", "supervisor_node")

    # ==================================================================
    # Conditional edges: supervisor → specialist | response
    # ==================================================================

    graph.add_conditional_edges(
        "supervisor_node",
        route_by_intent,
        {
            "medical_node": "medical_node",
            "scheduling_node": "scheduling_node",
            "knowledge_node": "knowledge_node",
            "response_node": "response_node",
        },
    )

    # ==================================================================
    # Conditional edges: specialist → supervisor (handoff) | response
    # ==================================================================

    for specialist in (
        "medical_node",
        "scheduling_node",
        "knowledge_node",
    ):
        graph.add_conditional_edges(
            specialist,
            should_continue,
            {
                "supervisor_node": "supervisor_node",
                "response_node": "response_node",
                "mcp_tool_node": "mcp_tool_node",
            },
        )

    # ==================================================================
    # Conditional edges: tool → specialist (resume)
    # ==================================================================

    graph.add_conditional_edges(
        "mcp_tool_node",
        route_after_tool,
        {
            "medical_node": "medical_node",
            "scheduling_node": "scheduling_node",
            "knowledge_node": "knowledge_node",
            "response_node": "response_node",
        },
    )

    # ==================================================================
    # Terminal edge: response → END
    # ==================================================================

    graph.add_edge("response_node", END)

    # ==================================================================
    # Compile with MemorySaver
    # ==================================================================

    memory = MemorySaver()
    compiled = graph.compile(checkpointer=memory)

    logger.info(
        "MedAI LangGraph compiled",
        nodes=6,
        recursion_limit=settings.langgraph_recursion_limit,
    )

    return compiled
