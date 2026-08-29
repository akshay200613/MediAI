"""
Security context for AI agent and tool execution.
Provides task-local contextvars so tools can securely access and enforce
the caller's authenticated user_id, patient_id, and role without relying
on untrusted LLM arguments.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolSecurityContext:
    user_id: str
    patient_id: str | None = None
    role: str = "patient"
    email: str | None = None
    full_name: str | None = None


# Thread/Task-local security context for the current async execution
_current_tool_security_context: contextvars.ContextVar[ToolSecurityContext | None] = (
    contextvars.ContextVar("tool_security_context", default=None)
)


def set_tool_security_context(
    user_id: str,
    patient_id: str | None = None,
    role: str = "patient",
    email: str | None = None,
    full_name: str | None = None,
) -> contextvars.Token:
    """Set the authenticated security context for the current async task."""
    ctx = ToolSecurityContext(
        user_id=str(user_id),
        patient_id=str(patient_id) if patient_id else None,
        role=role,
        email=email,
        full_name=full_name,
    )
    return _current_tool_security_context.set(ctx)


def get_tool_security_context() -> ToolSecurityContext | None:
    """Get the active authenticated security context."""
    return _current_tool_security_context.get()


def reset_tool_security_context(token: contextvars.Token) -> None:
    """Reset the security context using the token returned by set."""
    _current_tool_security_context.reset(token)
