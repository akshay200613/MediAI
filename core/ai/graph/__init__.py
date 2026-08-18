"""
LangGraph Multi-Agent Orchestration for MediAI.

Exports the graph builder so the rest of the application
can create and invoke the compiled agent graph.

Usage:

    from core.ai.graph import build_medai_graph

    graph = build_medai_graph()
    result = await graph.ainvoke(initial_state)
"""

from core.ai.graph.builder import build_medai_graph

__all__ = ["build_medai_graph"]
