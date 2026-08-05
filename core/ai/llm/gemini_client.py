"""
Gemini 2.5 Flash LLM Client – implements BaseLLMClient using Google Gen AI SDK.
"""

from typing import AsyncIterator

import google.generativeai as genai

from core.ai.llm.client import BaseLLMClient, LLMResponse, Message
from core.config.settings import settings
from core.config.logging import get_logger

logger = get_logger(__name__)


class GeminiClient(BaseLLMClient):
    """
    Gemini 2.5 Flash implementation.
    Handles text generation, streaming, and embedding.
    """

    def __init__(self) -> None:
        genai.configure(api_key=settings.google_api_key)
        self._model = genai.GenerativeModel(settings.gemini_model)
        self._embedding_model = settings.gemini_embedding_model

    def _to_gemini_history(
        self, messages: list[Message]
    ) -> tuple[list[dict], str]:
        """Convert Message list to Gemini history + last user message."""
        history = []
        last_user_message = ""

        for msg in messages:
            if msg.role == "system":
                # Gemini handles system prompts separately
                continue
            role = "user" if msg.role == "user" else "model"
            history.append({"role": role, "parts": [msg.content]})

        # Pop the last user message (it's sent as input, not history)
        if history and history[-1]["role"] == "user":
            last_user_message = history.pop()["parts"][0]

        return history, last_user_message

    async def generate(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Generate a full response from Gemini."""
        temp = temperature if temperature is not None else settings.gemini_temperature
        max_tok = max_tokens if max_tokens is not None else settings.gemini_max_tokens

        generation_config = genai.types.GenerationConfig(
            temperature=temp,
            max_output_tokens=max_tok,
        )

        # Extract system prompt from messages if not provided
        if system_prompt is None:
            system_msgs = [m for m in messages if m.role == "system"]
            if system_msgs:
                system_prompt = system_msgs[0].content

        model = genai.GenerativeModel(
            settings.gemini_model,
            system_instruction=system_prompt,
            generation_config=generation_config,
        )

        history, user_input = self._to_gemini_history(messages)
        chat = model.start_chat(history=history)

        try:
            response = await chat.send_message_async(user_input)
            return LLMResponse(
                content=response.text,
                model=settings.gemini_model,
                usage={
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count,
                },
            )
        except Exception as e:
            logger.error("Gemini generation failed", error=str(e))
            raise

    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream tokens from Gemini."""
        temp = temperature if temperature is not None else settings.gemini_temperature

        system_msgs = [m for m in messages if m.role == "system"]
        if system_prompt is None and system_msgs:
            system_prompt = system_msgs[0].content

        model = genai.GenerativeModel(
            settings.gemini_model,
            system_instruction=system_prompt,
            generation_config=genai.types.GenerationConfig(temperature=temp),
        )

        history, user_input = self._to_gemini_history(messages)
        chat = model.start_chat(history=history)

        async for chunk in await chat.send_message_async(user_input, stream=True):
            if chunk.text:
                yield chunk.text

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector using Gemini's embedding model."""
        result = await genai.embed_content_async(
            model=self._embedding_model,
            content=text,
            task_type="retrieval_document",
        )
        return result["embedding"]


# Singleton instance
_gemini_client: GeminiClient | None = None


def get_llm_client() -> GeminiClient:
    """Get singleton Gemini client."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
