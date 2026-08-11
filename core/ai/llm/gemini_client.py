"""
Gemini LLM Client.

Implements BaseLLMClient using Google's current Gen AI SDK.
Handles text generation, streaming, and embeddings.
"""

from typing import AsyncIterator

from google import genai
from google.genai import types

from core.ai.llm.client import BaseLLMClient, LLMResponse, Message
from core.config.logging import get_logger
from core.config.settings import settings


logger = get_logger(__name__)


class GeminiClient(BaseLLMClient):
    """
    Gemini implementation of the unified LLM client.

    Responsibilities:
    - Text generation
    - Streaming generation
    - Text embeddings
    """

    def __init__(self) -> None:
        self._client = genai.Client(
            api_key=settings.google_api_key,
        )

        self._model = settings.gemini_model
        self._embedding_model = settings.gemini_embedding_model
        self._embedding_dimension = settings.gemini_embedding_dimension

    @staticmethod
    def _to_gemini_contents(
        messages: list[Message],
    ) -> tuple[list[types.Content], str]:
        """
        Convert internal messages to Gemini contents.

        Returns:
            Tuple containing:
            - Conversation history
            - Latest user message
        """

        history: list[types.Content] = []
        last_user_message = ""

        for message in messages:
            if message.role == "system":
                continue

            role = "user" if message.role == "user" else "model"

            history.append(
                types.Content(
                    role=role,
                    parts=[
                        types.Part.from_text(
                            text=message.content,
                        )
                    ],
                )
            )

        if history and history[-1].role == "user":
            last_user_message = history.pop().parts[0].text

        return history, last_user_message

    async def generate(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Generate a complete response from Gemini."""

        temperature = (
            temperature
            if temperature is not None
            else settings.gemini_temperature
        )

        max_tokens = (
            max_tokens
            if max_tokens is not None
            else settings.gemini_max_tokens
        )

        if system_prompt is None:
            system_messages = [
                message
                for message in messages
                if message.role == "system"
            ]

            if system_messages:
                system_prompt = system_messages[0].content

        history, user_input = self._to_gemini_contents(messages)

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_prompt,
        )

        try:
            response = await self._client.aio.chats.create(
                model=self._model,
                history=history,
                config=config,
            ).send_message(
                message=user_input,
            )

            usage = {}

            if response.usage_metadata:
                usage = {
                    "prompt_tokens": (
                        response.usage_metadata.prompt_token_count
                    ),
                    "completion_tokens": (
                        response.usage_metadata.candidates_token_count
                    ),
                    "total_tokens": (
                        response.usage_metadata.total_token_count
                    ),
                }

            return LLMResponse(
                content=response.text or "",
                model=self._model,
                usage=usage,
            )

        except Exception as exc:
            logger.error(
                "Gemini generation failed",
                error=str(exc),
                model=self._model,
            )
            raise

    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream a response from Gemini."""

        temperature = (
            temperature
            if temperature is not None
            else settings.gemini_temperature
        )

        if system_prompt is None:
            system_messages = [
                message
                for message in messages
                if message.role == "system"
            ]

            if system_messages:
                system_prompt = system_messages[0].content

        history, user_input = self._to_gemini_contents(messages)

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_prompt,
        )

        try:
            chat = self._client.aio.chats.create(
                model=self._model,
                history=history,
                config=config,
            )

            async for chunk in await chat.send_message_stream(
                message=user_input,
            ):
                if chunk.text:
                    yield chunk.text

        except Exception as exc:
            logger.error(
                "Gemini streaming failed",
                error=str(exc),
                model=self._model,
            )
            raise

    async def embed(
        self,
        text: str,
        *,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> list[float]:
        """
        Generate an embedding using Gemini.

        RETRIEVAL_DOCUMENT:
            Used when indexing documents into Qdrant.

        RETRIEVAL_QUERY:
            Used when embedding a user's search/query text.
        """

        try:
            response = await self._client.aio.models.embed_content(
                model=self._embedding_model,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=self._embedding_dimension,
                ),
            )

            if not response.embeddings:
                raise RuntimeError(
                    "Gemini returned no embedding."
                )

            embedding = response.embeddings[0].values

            if not embedding:
                raise RuntimeError(
                    "Gemini returned an empty embedding."
                )

            if len(embedding) != self._embedding_dimension:
                raise RuntimeError(
                    "Unexpected embedding dimension: "
                    f"expected {self._embedding_dimension}, "
                    f"got {len(embedding)}"
                )

            return list(embedding)

        except Exception as exc:
            logger.error(
                "Gemini embedding failed",
                error=str(exc),
                model=self._embedding_model,
                task_type=task_type,
            )
            raise

# Singleton

_gemini_client: GeminiClient | None = None


def get_llm_client() -> GeminiClient:
    """Return the singleton Gemini client."""

    global _gemini_client

    if _gemini_client is None:
        _gemini_client = GeminiClient()

    return _gemini_client