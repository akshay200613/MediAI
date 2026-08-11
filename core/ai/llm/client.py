"""
Unified LLM Client Interface.
Abstract base – allows swapping Gemini for any other provider.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class Message:
    """A single chat message."""
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class LLMResponse:
    """Structured response from any LLM."""
    content: str
    model: str
    usage: dict = field(default_factory=dict)
    finish_reason: str = "stop"


class BaseLLMClient(ABC):
    """Abstract base for all LLM clients."""

    @abstractmethod
    async def generate(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream tokens from the LLM."""
        ...

    @abstractmethod
    async def embed(
        self,
        text: str,
        *,
        task_type: str = "RETRIEVAL_DOCUMENT",
)   -> list[float]:
        """Generate an embedding vector for the given text."""
        ...
        