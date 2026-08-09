"""
Base Agent – abstract foundation for all AI agents.
Defines the AgentContext, AgentResponse, and BaseAgent interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from core.ai.llm.client import BaseLLMClient, Message


@dataclass
class AgentContext:
    """Context passed to an agent for a single invocation."""
    session_id: str
    user_id: str
    domain: str
    messages: list[Message] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Structured response from an agent."""
    content: str
    agent_name: str = ""
    sources: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract base for all AI agents.
    Subclasses implement `run()` with domain-specific logic.
    """

    name: str = "base_agent"
    description: str = ""
    system_prompt: str = ""

    def __init__(self, llm_client: BaseLLMClient) -> None:
        self.llm = llm_client

    async def invoke(self, context: AgentContext) -> AgentResponse:
        """
        Public entry point – wraps `run()` with error handling.
        """
        try:
            return await self.run(context)
        except Exception as e:
            return AgentResponse(
                content=f"I encountered an error processing your request: {e}",
                agent_name=self.name,
            )

    @abstractmethod
    async def run(self, context: AgentContext) -> AgentResponse:
        """Implement domain-specific agent logic."""
        ...
