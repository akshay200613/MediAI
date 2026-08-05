"""
FastMCP Server – exposes all registered tools via MCP protocol.
Supports SSE transport for real-time tool streaming.
"""

from fastmcp import FastMCP

from core.ai.mcp.tool_registry import tool_registry
from core.config.settings import settings
from core.config.logging import get_logger

logger = get_logger(__name__)

# Initialize FastMCP server
mcp_server = FastMCP(
    name="AI ServiceOS MCP",
    instructions=(
        "You are the AI ServiceOS tool server. "
        "You provide tools for clinic management, scheduling, medical records, "
        "and AI-powered assistance."
    ),
)


def register_all_tools() -> None:
    """Register all tools from the ToolRegistry into the FastMCP server."""
    tools = tool_registry.list_all()
    logger.info("Registering MCP tools", count=len(tools))

    for tool_def in tools:
        # FastMCP accepts standard Python async functions
        mcp_server.add_tool(
            tool_def.func,
            name=tool_def.name,
            description=tool_def.description,
        )
        logger.debug("MCP tool registered", tool=tool_def.name)


if __name__ == "__main__":
    # Import all domain tools to trigger registration
    from domains.medai.ai.mcp import tools  # noqa: F401

    register_all_tools()

    logger.info(
        "Starting MCP server",
        host=settings.mcp_server_host,
        port=settings.mcp_server_port,
        transport=settings.mcp_transport,
    )

    mcp_server.run(
        transport=settings.mcp_transport,
        host=settings.mcp_server_host,
        port=settings.mcp_server_port,
    )
