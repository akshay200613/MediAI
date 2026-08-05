"""
MCP Tool Registry – central registration and auto-discovery of all MCP tools.
Domain tools register themselves here via decorators.
"""

from typing import Callable, Any
from dataclasses import dataclass, field

from core.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ToolDefinition:
    """Metadata for a registered MCP tool."""
    name: str
    description: str
    func: Callable
    domain: str = "platform"
    tags: list[str] = field(default_factory=list)


class ToolRegistry:
    """
    Singleton registry for all MCP tools.
    Tools are registered via the @tool decorator and auto-discovered at startup.
    """

    _instance: "ToolRegistry | None" = None
    _tools: dict[str, ToolDefinition] = {}

    def __new__(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance

    def register(
        self,
        func: Callable,
        *,
        name: str | None = None,
        description: str = "",
        domain: str = "platform",
        tags: list[str] | None = None,
    ) -> Callable:
        """Register a tool function."""
        tool_name = name or func.__name__
        self._tools[tool_name] = ToolDefinition(
            name=tool_name,
            description=description or func.__doc__ or "",
            func=func,
            domain=domain,
            tags=tags or [],
        )
        logger.debug("Tool registered", tool=tool_name, domain=domain)
        return func

    def tool(
        self,
        *,
        name: str | None = None,
        description: str = "",
        domain: str = "platform",
        tags: list[str] | None = None,
    ) -> Callable:
        """Decorator factory for registering MCP tools."""
        def decorator(func: Callable) -> Callable:
            return self.register(
                func,
                name=name,
                description=description,
                domain=domain,
                tags=tags,
            )
        return decorator

    def register_all(self, tools: list[Callable]) -> None:
        """Bulk register a list of tool functions (for domain registration)."""
        for tool_func in tools:
            self.register(tool_func, domain="domain")

    def get(self, name: str) -> ToolDefinition | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_all(self) -> list[ToolDefinition]:
        """Get all registered tools."""
        return list(self._tools.values())

    def list_by_domain(self, domain: str) -> list[ToolDefinition]:
        """Get all tools for a specific domain."""
        return [t for t in self._tools.values() if t.domain == domain]

    def get_langchain_tools(self) -> list:
        """Convert registered tools to LangChain Tool objects for use in agents."""
        from langchain_core.tools import Tool
        return [
            Tool(
                name=t.name,
                description=t.description,
                func=t.func,
                coroutine=t.func if __import__("asyncio").iscoroutinefunction(t.func) else None,
            )
            for t in self._tools.values()
        ]


# Singleton instance
tool_registry = ToolRegistry()
