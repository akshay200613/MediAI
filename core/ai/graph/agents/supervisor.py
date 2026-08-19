"""
Supervisor Agent – orchestration brain of the MedAI graph.

Responsibilities:

    1. Validate the reception agent's intent classification
    2. Decide which specialist agent to route to
    3. Handle multi-turn flows requiring sequential agent calls
    4. Override routing when conversation context suggests
       a different specialist is needed

The supervisor does NOT answer the user's question directly.
It only makes routing decisions.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import BaseMessage

from core.ai.llm.litellm_client import get_llm_client
from core.ai.llm.client import Message
from core.config.logging import get_logger
from core.config.settings import settings


logger = get_logger(__name__)


SUPERVISOR_SYSTEM_PROMPT = """\
You are the Supervisor Agent for MedAI. You decide which specialist
agent should handle the user's request.

You receive:
- The classified intent from the reception agent
- Extracted entities
- Conversation history

Your job is to:
1. Validate or override the intent classification based on full context
2. Decide the best specialist agent to handle this request

Available specialists:
- "medical_node": for symptoms, diagnoses, treatments, clinical questions
- "scheduling_node": for appointment booking, rescheduling, cancellation
- "knowledge_node": for hospital info, facilities, insurance, policies
- "response_node": for greetings, small talk, or simple general queries

Return ONLY valid JSON:
{
  "current_agent": "medical_node",
  "intent": "medical",
  "reasoning": "User is describing symptoms that need clinical assessment"
}

Do NOT answer the user's question. Return ONLY the routing JSON.
"""


class SupervisorAgent:
    """
    Routes requests to the appropriate specialist agent.

    The supervisor can override the reception agent's initial
    classification when conversation context provides stronger
    signals about the user's actual need.
    """

    def __init__(self) -> None:
        self.llm = get_llm_client()

    async def process(
        self,
        intent: str,
        entities: dict[str, Any],
        conversation_history: list[BaseMessage] | None = None,
    ) -> dict[str, Any]:
        """
        Determine routing for the current request.

        Args:
            intent:
                Intent classified by the reception agent.

            entities:
                Entities extracted by the reception agent.

            conversation_history:
                Prior conversation for context.

        Returns:
            Dict with ``current_agent`` and optionally
            overridden ``intent``.
        """

        # Fast-path: high-confidence simple intents
        if intent in ("medical", "scheduling", "knowledge"):
            node = f"{intent}_node"

            logger.debug(
                "Supervisor fast-path routing",
                intent=intent,
                node=node,
            )

            return {
                "current_agent": node,
                "intent": intent,
            }

        # General / unknown intents → route directly to response_node
        # No LLM call needed — saves an API request per message
        logger.debug(
            "Supervisor deterministic routing (no LLM call)",
            intent=intent,
            node="response_node",
        )

        return {
            "current_agent": "response_node",
            "intent": "general",
        }

    @staticmethod
    def _parse_routing(content: str) -> dict[str, Any]:
        """Parse the LLM's routing JSON response."""

        content = content.strip()

        # Robustly extract JSON block by finding the first '{' and last '}'
        start_idx = content.find("{")
        end_idx = content.rfind("}")
        
        if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
            content = content[start_idx:end_idx + 1]

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse supervisor response",
                content=content[:200],
            )
            return {
                "current_agent": "response_node",
                "intent": "general",
            }

        valid_nodes = {
            "medical_node",
            "scheduling_node",
            "knowledge_node",
            "response_node",
        }

        current_agent = data.get("current_agent", "response_node")

        if current_agent not in valid_nodes:
            current_agent = "response_node"

        return {
            "current_agent": current_agent,
            "intent": data.get("intent", "general"),
            "reasoning": data.get("reasoning", ""),
        }
