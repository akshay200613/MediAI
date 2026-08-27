"""
Message sanitization utilities.

Strips provider-specific fields (e.g. Gemini``reasoning_content``) from
LangChain message objects before they are forwarded to another provider
(e.g. Groq on fallback) that does not understand those fields.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage

# Fields injected by Gemini thinking/reasoning models that are NOT accepted
# by other providers (Groq, OpenAI-compatible APIs, etc.).
_PROVIDER_ONLY_KWARGS: frozenset[str] = frozenset(
    {
        "reasoning_content",   # Gemini thinking / reasoning output
        "thinking_blocks",     # Anthropic-style thinking blocks (via Gemini)
        "parsed",              # Gemini structured-output artefact
    }
)


def sanitize_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    """
    Return a cleaned copy of *messages* with provider-specific
    ``additional_kwargs`` removed from every ``AIMessage``.

    Non-AIMessage objects (HumanMessage, SystemMessage, ToolMessage, ...)
    are returned as-is.

    This is a *copy* operation -- the original objects in state["messages"]
    are left unchanged so LangGraph state reducer does not see mutations.
    """
    sanitized: list[BaseMessage] = []
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.additional_kwargs:
            bad_keys = _PROVIDER_ONLY_KWARGS & msg.additional_kwargs.keys()
            if bad_keys:
                clean_kwargs = {
                    k: v
                    for k, v in msg.additional_kwargs.items()
                    if k not in bad_keys
                }
                msg = msg.copy(update={"additional_kwargs": clean_kwargs})
        sanitized.append(msg)
    return sanitized
