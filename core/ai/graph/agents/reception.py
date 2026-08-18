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

from core.ai.llm.gemini_client import get_llm_client
from core.ai.llm.client import Message
from core.config.logging import get_logger


logger = get_logger(__name__)


RECEPTION_SYSTEM_PROMPT = """\
You are the Reception Agent for MedAI, a hospital management system.

Your ONLY job is to:
1. Classify the user's intent into exactly ONE of these categories:
   - "medical": symptoms, diagnoses, treatments, medications, clinical questions
   - "scheduling": booking, rescheduling, cancelling appointments, doctor availability
   - "knowledge": hospital info, facilities, insurance, contact details, policies
   - "general": greetings, small talk, unclear, or out-of-scope queries

2. Extract relevant entities from the message:
   - patient_name: if a patient is mentioned
   - doctor_name: if a doctor is mentioned
   - specialty: if a medical specialty is mentioned
   - date: if a date/time is mentioned (ISO 8601)
   - symptoms: list of symptoms mentioned
   - appointment_id: if an appointment reference is mentioned

Return ONLY valid JSON in this exact format:
{
  "intent": "medical",
  "entities": {
    "symptoms": ["headache", "fever"],
    "specialty": "neurology"
  },
  "confidence": 0.95
}

Do NOT answer the user's question. Do NOT generate conversational text.
Return ONLY the JSON classification.
"""


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
                temperature=0.0,
                max_tokens=500,
            )

            result = self._parse_classification(response.content)

            logger.debug(
                "Reception classification",
                intent=result["intent"],
                confidence=result.get("confidence", 0.0),
                entities=result.get("entities", {}),
            )

            return result

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
        """Parse the LLM's JSON classification response."""

        content = content.strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            lines = content.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse reception response as JSON",
                content=content[:200],
            )
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
