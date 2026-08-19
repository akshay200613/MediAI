"""
LiteLLM Client with Router-based Fallback & Caching.

Uses litellm.Router to:
  - Route each agent to its configured primary model
  - Automatically fall back to Groq on rate-limit / timeout
  - Cache identical prompts in-memory (or Redis when available)
  - Retry with exponential backoff
"""

from __future__ import annotations

from typing import AsyncIterator

import litellm
from litellm import Router, aembedding

from core.ai.llm.client import BaseLLMClient, LLMResponse, Message
from core.config.logging import get_logger
from core.config.settings import settings


logger = get_logger(__name__)

# Suppress noisy LiteLLM debug output in dev
litellm.suppress_debug_info = True


# ============================================================================
# Router Builder
# ============================================================================


def _build_router() -> Router:
    """
    Create and configure the LiteLLM Router singleton.

    Uses the ``fallbacks`` parameter so the Router always tries
    the primary (Gemini) model first, and only switches to the
    fallback (Groq) when it receives a RateLimitError, Timeout,
    or other API error.
    """

    # ------------------------------------------------------------------
    # Collect unique primary and fallback models
    # ------------------------------------------------------------------

    agents = ["reception", "medical", "scheduling", "knowledge", "supervisor"]

    primary_models: set[str] = set()
    fallback_models: set[str] = set()

    for agent in agents:
        primary_models.add(getattr(settings, f"model_{agent}"))
        if settings.groq_api_key:
            fallback_models.add(getattr(settings, f"model_fallback_{agent}"))

    # ------------------------------------------------------------------
    # Build model_list (one entry per unique model)
    # ------------------------------------------------------------------

    model_list: list[dict] = []

    for model in primary_models:
        model_list.append(
            {
                "model_name": model,
                "litellm_params": {
                    "model": model,
                    "api_key": settings.gemini_api_key,
                },
            }
        )

    for model in fallback_models:
        model_list.append(
            {
                "model_name": model,
                "litellm_params": {
                    "model": model,
                    "api_key": settings.groq_api_key,
                },
            }
        )

    # ------------------------------------------------------------------
    # Build fallback mapping: primary → [fallback1, fallback2, ...]
    # ------------------------------------------------------------------

    fallbacks: list[dict[str, list[str]]] = []

    if settings.groq_api_key:
        # Map each unique primary model to its corresponding fallbacks
        fallback_map: dict[str, set[str]] = {}

        for agent in agents:
            primary = getattr(settings, f"model_{agent}")
            fallback = getattr(settings, f"model_fallback_{agent}")

            if primary not in fallback_map:
                fallback_map[primary] = set()
            fallback_map[primary].add(fallback)

        for primary, fb_set in fallback_map.items():
            fallbacks.append({primary: list(fb_set)})

    # ------------------------------------------------------------------
    # Cache configuration
    # ------------------------------------------------------------------

    cache_config = None
    if settings.litellm_cache_enabled:
        if settings.redis_url and settings.redis_password:
            cache_config = {
                "type": "redis",
                "host": settings.redis_host,
                "port": settings.redis_port,
                "password": settings.redis_password,
            }
        else:
            cache_config = {"type": "local"}

    # ------------------------------------------------------------------
    # Create Router
    # ------------------------------------------------------------------

    router = Router(
        model_list=model_list,
        fallbacks=fallbacks if fallbacks else None,
        num_retries=settings.litellm_num_retries,
        timeout=settings.litellm_request_timeout,
        retry_after=0,  # don't wait between retries — fail over immediately
        cache_responses=settings.litellm_cache_enabled,
        set_verbose=False,
        allowed_fails=0,  # switch to fallback on FIRST error
    )

    # ------------------------------------------------------------------
    # Module-level settings (retries only — NOT fallbacks,
    # which cause infinite recursion when set at module level)
    # ------------------------------------------------------------------

    litellm.num_retries = settings.litellm_num_retries

    # Enable response caching
    if settings.litellm_cache_enabled and cache_config:
        litellm.cache = litellm.Cache(**cache_config)

    logger.info(
        "LiteLLM Router initialized",
        primary_models=list(primary_models),
        fallback_models=list(fallback_models) if fallback_models else "none",
        fallbacks=fallbacks if fallbacks else "none",
        retries=settings.litellm_num_retries,
        timeout=settings.litellm_request_timeout,
        cache=settings.litellm_cache_enabled,
    )

    return router


# ============================================================================
# Client
# ============================================================================


class LiteLLMClient(BaseLLMClient):
    """
    LiteLLM Router-backed LLM client.

    All calls go through the Router which handles:
      - Fallback routing (primary → fallback on error)
      - Rate limit retries with exponential backoff
      - Response caching
    """

    def __init__(self, router: Router) -> None:
        self._router = router
        self._default_model = settings.model_supervisor
        self._embedding_model = settings.gemini_embedding_model

    @staticmethod
    def _to_litellm_messages(
        messages: list[Message],
        system_prompt: str | None = None,
    ) -> list[dict[str, str]]:
        """Convert internal messages to LiteLLM (OpenAI) format."""

        out: list[dict[str, str]] = []

        if system_prompt:
            out.append({"role": "system", "content": system_prompt})

        for message in messages:
            if message.role == "system" and system_prompt:
                continue
            out.append({"role": message.role, "content": message.content})

        return out

    async def generate(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Generate a response via the Router (with automatic fallback)."""

        model_name = model or self._default_model

        if system_prompt is None:
            system_messages = [m for m in messages if m.role == "system"]
            if system_messages:
                system_prompt = system_messages[0].content

        litellm_messages = self._to_litellm_messages(messages, system_prompt)

        try:
            response = await self._router.acompletion(
                model=model_name,
                messages=litellm_messages,
                temperature=(
                    temperature
                    if temperature is not None
                    else settings.gemini_temperature
                ),
                max_tokens=(
                    max_tokens
                    if max_tokens is not None
                    else settings.gemini_max_tokens
                ),
            )

            content = response.choices[0].message.content or ""
            usage_info = getattr(response, "usage", None)
            usage = {}
            if usage_info:
                usage = {
                    "prompt_tokens": usage_info.prompt_tokens,
                    "completion_tokens": usage_info.completion_tokens,
                    "total_tokens": usage_info.total_tokens,
                }

            # Log which model was actually used
            actual_model = getattr(response, "model", model_name)
            if actual_model != model_name:
                logger.info(
                    "Fallback model used",
                    requested=model_name,
                    actual=actual_model,
                )

            return LLMResponse(
                content=content,
                model=actual_model,
                usage=usage,
            )

        except Exception as exc:
            logger.error(
                "LiteLLM Router generation failed (all deployments)",
                error=str(exc),
                model=model_name,
            )
            raise

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream tokens via the Router (with automatic fallback)."""

        model_name = model or self._default_model

        if system_prompt is None:
            system_messages = [m for m in messages if m.role == "system"]
            if system_messages:
                system_prompt = system_messages[0].content

        litellm_messages = self._to_litellm_messages(messages, system_prompt)

        try:
            response_stream = await self._router.acompletion(
                model=model_name,
                messages=litellm_messages,
                temperature=(
                    temperature
                    if temperature is not None
                    else settings.gemini_temperature
                ),
                stream=True,
            )

            async for chunk in response_stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta

        except Exception as exc:
            logger.error(
                "LiteLLM Router streaming failed (all deployments)",
                error=str(exc),
                model=model_name,
            )
            raise

    async def embed(
        self,
        text: str,
        *,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> list[float]:
        """Generate embeddings (always via Gemini — no fallback needed)."""

        try:
            embed_model = (
                f"gemini/{self._embedding_model}"
                if not self._embedding_model.startswith("gemini/")
                else self._embedding_model
            )

            response = await aembedding(
                model=embed_model,
                input=text,
            )

            return response.data[0]["embedding"]

        except Exception as exc:
            logger.error(
                "LiteLLM embedding failed",
                error=str(exc),
                model=self._embedding_model,
            )
            raise


# ============================================================================
# Singleton
# ============================================================================

_router: Router | None = None
_litellm_client: LiteLLMClient | None = None


def get_router() -> Router:
    """Return the singleton Router instance."""

    global _router

    if _router is None:
        _router = _build_router()

    return _router


def get_llm_client() -> LiteLLMClient:
    """Return the singleton LiteLLM client backed by the Router."""

    global _litellm_client

    if _litellm_client is None:
        _litellm_client = LiteLLMClient(router=get_router())

    return _litellm_client
