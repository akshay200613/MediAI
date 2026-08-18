"""
FastMCP Server for MedAI – registers and exposes all tools.

Runs in-process (stdio transport) for zero-overhead tool
invocation within the LangGraph agents.

Architecture:

    LangGraph Agent
         ↓
    FastMCP Server (in-process)
         ↓
    ┌────────────┬─────────────────┬────────────────┐
    │  Patient   │  Appointment    │   Database     │
    │   Tools    │    Tools        │    Tools       │
    └────────────┴─────────────────┴────────────────┘
         ↓              ↓                ↓
    PatientService  AppointmentService  RAGPipeline

Usage:

    from core.ai.graph.tools.server import mcp_server

    # The server is ready to be used with LangGraph's
    # tool-calling interface.
"""

from __future__ import annotations

from fastmcp import FastMCP

from core.config.logging import get_logger


logger = get_logger(__name__)


# ============================================================================
# FastMCP Server instance
# ============================================================================

mcp_server = FastMCP(
    name="MedAI Tools",
    instructions=(
        "MedAI tool server providing access to patient records, "
        "appointment management, and hospital knowledge base. "
        "Use these tools to look up patient information, manage "
        "appointments, and query the knowledge base."
    ),
)


def register_all_tools() -> None:
    """
    Register all tool modules with the MCP server.

    Import each tool module to trigger its ``@mcp_server.tool()``
    registrations.
    """

    # Each module decorates functions with @mcp_server.tool()
    # on import, so we just need to import them.
    import core.ai.graph.tools.patient_tools  # noqa: F401
    import core.ai.graph.tools.appointment_tools  # noqa: F401
    import core.ai.graph.tools.database_tools  # noqa: F401

    logger.info(
        "MCP tools registered",
        server=mcp_server.name,
    )


# Register tools on module load
register_all_tools()
