"""
Reception Agent – first contact in the MedAI graph.

Responsibilities:

    1. Intent classification (medical / scheduling / knowledge / general)
    2. Named entity extraction (patient, doctor, date, symptom, etc.)
    3. Greeting and disambiguation for unclear queries

The reception agent does NOT answer the user's question.
It only classifies and extracts, then hands off to the supervisor.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import BaseMessage

from core.ai.llm.litellm_client import get_llm_client, AIServiceUnavailableError
from core.ai.llm.client import Message
from core.config.logging import get_logger
from core.config.settings import settings


logger = get_logger(__name__)


import yaml
from pathlib import Path

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "reception.yaml"
with open(_PROMPT_PATH, "r", encoding="utf-8") as _f:
    RECEPTION_SYSTEM_PROMPT = yaml.safe_load(_f)["system_prompt"]


class ReceptionAgent:
    """
    Classifies user intent and extracts entities.

    This agent uses the Gemini LLM with structured output
    to produce a JSON classification that the supervisor
    uses for routing.
    """

    def __init__(self) -> None:
        self.llm = get_llm_client()

    async def process(
        self,
        message: str,
        conversation_history: list[BaseMessage] | None = None,
    ) -> dict[str, Any]:
        """
        Classify intent and extract entities.

        Args:
            message:
                The user's latest message text.

            conversation_history:
                Prior conversation for context.

        Returns:
            Dict with ``intent``, ``entities``, and ``confidence``.
        """

        if not message.strip():
            return {
                "intent": "general",
                "entities": {},
                "confidence": 1.0,
            }

        prompt = (
            f"Classify the following user message.\n\n"
            f"USER MESSAGE:\n{message}"
        )

        try:
            response = await self.llm.generate(
                messages=[Message(role="user", content=prompt)],
                system_prompt=RECEPTION_SYSTEM_PROMPT,
                max_tokens=500,
                model=settings.model_reception,
            )

            result = self._parse_classification(response.content)

            logger.debug(
                "Reception classification",
                intent=result["intent"],
                confidence=result.get("confidence", 0.0),
                entities=result.get("entities", {}),
            )

            return result

        except AIServiceUnavailableError:
            logger.warning("Reception agent hit rate limit")
            return {
                "intent": "rate_limit",
                "entities": {},
                "confidence": 0.0,
            }
        except Exception as exc:
            logger.error(
                "Reception agent failed",
                error=str(exc),
            )

            # Safe fallback: route to general
            return {
                "intent": "general",
                "entities": {},
                "confidence": 0.0,
            }

    @staticmethod
    def _parse_classification(content: str) -> dict[str, Any]:
        """Parse the LLM's JSON classification response robustly."""
        import re
        content = content.strip()

        # Try to find a JSON block in the output
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

        try:
            from langchain_core.utils.json import parse_partial_json
            data = parse_partial_json(content)
            if not isinstance(data, dict):
                data = {}
        except Exception as e:
            from core.config.logging import get_logger
            logger = get_logger(__name__)
            logger.error("Failed to parse reception JSON", error=str(e), content=content)
            return {
                "intent": "general",
                "entities": {},
                "confidence": 0.0,
            }

        # Validate intent
        valid_intents = {"medical", "scheduling", "knowledge", "general"}
        intent = data.get("intent", "general")

        if intent not in valid_intents:
            intent = "general"

        return {
            "intent": intent,
            "entities": data.get("entities", {}),
            "confidence": float(data.get("confidence", 0.5)),
        }
