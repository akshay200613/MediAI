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

from typing import Any, Literal

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field, field_validator

from core.ai.llm.litellm_client import get_llm_client
from core.ai.llm.client import Message
from core.config.logging import get_logger
from core.config.settings import settings


logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Structured output schema
# ─────────────────────────────────────────────────────────────────────────────

class ReceptionEntities(BaseModel):
    """Named entities extracted from the user message."""
    patient_name: str | None = Field(default=None, description="Patient name if mentioned")
    doctor_name: str | None = Field(default=None, description="Doctor name if mentioned")
    specialty: str | None = Field(default=None, description="Medical specialty if mentioned")
    date: str | None = Field(default=None, description="Date or time reference in ISO 8601 if mentioned")
    symptoms: list[str] = Field(default_factory=list, description="Symptoms mentioned by the user")
    appointment_id: str | None = Field(default=None, description="Appointment ID/reference if mentioned")


class ReceptionClassification(BaseModel):
    """Structured output produced by the Reception Agent."""

    intent: Literal["medical", "scheduling", "knowledge", "general"] = Field(
        description="Classified intent category for this user message"
    )
    entities: ReceptionEntities = Field(
        default_factory=ReceptionEntities,
        description="Named entities extracted from the message",
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Classification confidence between 0.0 and 1.0",
    )

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v: Any) -> float:
        try:
            return max(0.0, min(1.0, float(v)))
        except (TypeError, ValueError):
            return 0.5


# ─────────────────────────────────────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────────────────────────────────────

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

Return ONLY valid JSON matching this exact schema:
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


# ─────────────────────────────────────────────────────────────────────────────
# Reception Agent
# ─────────────────────────────────────────────────────────────────────────────

class ReceptionAgent:
    """
    Classifies user intent and extracts entities.

    Uses Pydantic-validated structured output to guarantee the LLM always
    returns a well-typed ``ReceptionClassification`` object. Falls back to
    safe defaults on any parse/LLM failure so the graph never stalls.
    """

    # Safe fallback returned on any error
    _FALLBACK: dict[str, Any] = {
        "intent": "general",
        "entities": {},
        "confidence": 0.0,
    }

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

        except Exception as exc:
            logger.error(
                "Reception agent failed",
                error=str(exc),
            )
            return self._FALLBACK.copy()

    @staticmethod
    def _parse_classification(content: str) -> dict[str, Any]:
        """
        Parse the LLM response into a validated ``ReceptionClassification``.

        Strips markdown fences, then validates through the Pydantic model.
        Any validation error produces a safe general-intent fallback.
        """

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
            import json
            from langchain_core.utils.json import parse_partial_json

            # Prefer strict JSON parse; fall back to LangChain's lenient partial parser
            try:
                raw = json.loads(content)
            except json.JSONDecodeError:
                raw = parse_partial_json(content)

            if not isinstance(raw, dict):
                raise ValueError(f"Expected dict, got {type(raw).__name__}")

            # Validate via Pydantic — raises ValidationError on bad data
            classification = ReceptionClassification.model_validate(raw)

            return {
                "intent": classification.intent,
                "entities": classification.entities.model_dump(exclude_none=True),
                "confidence": classification.confidence,
            }

        except Exception as exc:
            logger.warning(
                "Failed to parse reception response as JSON; defaulting to general",
                content=content[:200],
                error=str(exc),
            )
            return {
                "intent": "general",
                "entities": {},
                "confidence": 0.0,
            }
