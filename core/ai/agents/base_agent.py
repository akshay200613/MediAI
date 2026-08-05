"""
Abstract Base Agent – all domain agents inherit from this.
Provides lifecycle hooks, tool integration, and logging.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from core.ai.llm.client import BaseLLMClient, Message
from core.config.logging import get_logger


@dataclass
class AgentContext:
    """Context passed to each agent invocation."""
    session_id: str
    user_id: str
    domain: str
    messages: list[Message] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Structured response from an agent."""
    content: str
    agent_name: str
    tool_calls: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract base agent class.

    All domain agents should:
    1. Inherit from BaseAgent
    2. Define `name`, `description`, and `system_prompt`
    3. Implement `run()`
    """

    name: str = "base_agent"
    description: str = "Base agent"
    system_prompt: str = "You are a helpful AI assistant."

    def __init__(self, llm_client: BaseLLMClient) -> None:
        self.llm = llm_client
        self.logger = get_logger(self.name)

    async def before_run(self, context: AgentContext) -> AgentContext:
        """Hook: called before agent execution. Override to preprocess context."""
        self.logger.info("Agent starting", agent=self.name, session=context.session_id)
        return context

    @abstractmethod
    async def run(self, context: AgentContext) -> AgentResponse:
        """Main agent execution logic. Must be implemented by subclasses."""
        ...

    async def after_run(self, response: AgentResponse, context: AgentContext) -> AgentResponse:
        """Hook: called after agent execution. Override to postprocess response."""
        self.logger.info(
            "Agent completed",
            agent=self.name,
            session=context.session_id,
            tools_used=len(response.tool_calls),
        )
        return response

    async def invoke(self, context: AgentContext) -> AgentResponse:
        """
        Full agent lifecycle: before_run → run → after_run.
        This is the public entrypoint.
        """
        context = await self.before_run(context)
        response = await self.run(context)
        response = await self.after_run(response, context)
        return response
