"""
LiteLLM Client with Router-based Fallback & Caching.

Uses litellm.Router to:
  - Route each agent to its configured primary model
  - Automatically fall back to Groq on rate-limit / timeout
  - Cache identical prompts in-memory (or Redis when available)
  - Retry with exponential backoff
"""

from __future__ import annotations

import time
from typing import AsyncIterator

import litellm
from litellm import Router, aembedding

from core.ai.llm.client import BaseLLMClient, LLMResponse, Message
from core.config.logging import get_logger
from core.config.settings import settings
from core.metrics import (
    llm_requests_total,
    llm_request_duration_seconds,
    llm_tokens_total,
    llm_cost_estimated_dollars,
    llm_fallbacks_total,
)

logger = get_logger(__name__)


class AIServiceUnavailableError(RuntimeError):
    """Raised when every LLM provider (primary + all fallbacks) has failed."""

    USER_MESSAGE = "The AI service is temporarily unavailable. Please try again."

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
        if settings.redis_url or settings.redis_host:
            cache_config = {
                "type": "redis",
                "host": settings.redis_host,
                "port": settings.redis_port,
                "password": settings.redis_password if settings.redis_password else None,
                "namespace": "medai:litellm",
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

        start_time = time.perf_counter()
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

            latency = time.perf_counter() - start_time
            content = response.choices[0].message.content or ""
            usage_info = getattr(response, "usage", None)
            usage = {}
            p_tokens = 0
            c_tokens = 0
            if usage_info:
                p_tokens = getattr(usage_info, "prompt_tokens", 0) or 0
                c_tokens = getattr(usage_info, "completion_tokens", 0) or 0
                usage = {
                    "prompt_tokens": p_tokens,
                    "completion_tokens": c_tokens,
                    "total_tokens": getattr(usage_info, "total_tokens", 0) or (p_tokens + c_tokens),
                }

            # Log which model was actually used
            actual_model = getattr(response, "model", model_name)
            is_fallback = (actual_model != model_name)

            # Record Prometheus Observability Metrics
            llm_request_duration_seconds.labels(model=actual_model).observe(latency)
            if is_fallback:
                llm_fallbacks_total.labels(from_model=model_name, to_model=actual_model).inc()
                llm_requests_total.labels(model=actual_model, outcome="success", fallback_used="true").inc()
                logger.info(
                    "Fallback model used",
                    requested=model_name,
                    actual=actual_model,
                    duration_sec=round(latency, 3),
                )
            else:
                llm_requests_total.labels(model=actual_model, outcome="success", fallback_used="false").inc()

            if p_tokens or c_tokens:
                llm_tokens_total.labels(model=actual_model, token_type="prompt").inc(p_tokens)
                llm_tokens_total.labels(model=actual_model, token_type="completion").inc(c_tokens)
                # Estimate cost ($0.15/1M input, $0.60/1M output for flash-grade models)
                cost = (p_tokens * 0.00000015) + (c_tokens * 0.00000060)
                try:
                    from litellm import completion_cost
                    cost = completion_cost(completion_response=response)
                except Exception:
                    pass
                llm_cost_estimated_dollars.labels(model=actual_model).inc(cost)

            return LLMResponse(
                content=content,
                model=actual_model,
                usage=usage,
            )

        except Exception as exc:
            llm_requests_total.labels(model=model_name, outcome="error", fallback_used="false").inc()
            logger.error(
                "LiteLLM Router generation failed (all deployments — Gemini and Groq both unavailable)",
                error=str(exc),
                model=model_name,
            )
            raise AIServiceUnavailableError(AIServiceUnavailableError.USER_MESSAGE) from exc

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
                "LiteLLM Router streaming failed (all deployments — Gemini and Groq both unavailable)",
                error=str(exc),
                model=model_name,
            )
            raise AIServiceUnavailableError(AIServiceUnavailableError.USER_MESSAGE) from exc

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
_router_settings_fingerprint: str | None = None


def _router_fingerprint() -> str:
    """Return a string that changes whenever any routing-relevant setting changes."""
    agents = ["reception", "medical", "scheduling", "knowledge", "supervisor"]
    parts = [
        settings.gemini_api_key,
        settings.groq_api_key,
    ]
    for agent in agents:
        parts.append(getattr(settings, f"model_{agent}", ""))
        parts.append(getattr(settings, f"model_fallback_{agent}", ""))
    return "|".join(parts)


def reset_router() -> None:
    """Force the Router (and LiteLLM client) to be rebuilt on the next call."""
    global _router, _litellm_client, _router_settings_fingerprint
    _router = None
    _litellm_client = None
    _router_settings_fingerprint = None
    logger.info("LiteLLM Router singleton reset – will be rebuilt on next request")


def get_router() -> Router:
    """Return the Router singleton, rebuilding it if settings have changed."""

    global _router, _router_settings_fingerprint

    current_fp = _router_fingerprint()
    if _router is None or _router_settings_fingerprint != current_fp:
        if _router is not None:
            logger.info(
                "LiteLLM Router settings changed – rebuilding",
                old_fp=_router_settings_fingerprint,
                new_fp=current_fp,
            )
        _router = _build_router()
        _router_settings_fingerprint = current_fp

    return _router


def get_llm_client() -> LiteLLMClient:
    """Return the singleton LiteLLM client backed by the Router."""

    global _litellm_client

    router = get_router()  # may rebuild if settings changed
    if _litellm_client is None or _litellm_client._router is not router:
        _litellm_client = LiteLLMClient(router=router)

    return _litellm_client


def get_fallback_chat_llm(
    primary_model: str,
    fallback_model: str,
    temperature: float = 1.0,
) -> "ChatLiteLLM":
    """
    Return a ``ChatLiteLLM`` instance that falls back to Groq on Gemini failure.

    ``ChatLiteLLM`` supports LangChain's ``bind_tools()`` interface required by
    the tool-calling agents (medical, scheduling).

    We use **litellm module-level fallbacks** (``litellm.fallbacks``) which are
    the most reliable way to configure fallback behaviour for ChatLiteLLM calls.
    The Router-level fallbacks only apply when using ``router.acompletion()`` —
    for direct ``ChatLiteLLM`` calls we must configure litellm globally instead.

    Args:
        primary_model:  Gemini model string  (e.g. ``gemini/gemini-3-flash-preview``).
        fallback_model: Groq model string    (e.g. ``groq/llama3-8b-8192``).
        temperature:    Sampling temperature for both models.
    """
    from langchain_litellm import ChatLiteLLM  # local import avoids circular dep

    # ------------------------------------------------------------------
    # Configure module-level fallbacks so any ChatLiteLLM call on the
    # primary model will automatically switch to the fallback on 429/5xx.
    # ------------------------------------------------------------------
    if settings.groq_api_key and fallback_model:
        # litellm.fallbacks format: list of {primary: [fallback, ...]}
        existing: list = getattr(litellm, "fallbacks", None) or []
        # Remove stale entry for this primary (settings may have changed)
        existing = [f for f in existing if primary_model not in f]
        existing.append({primary_model: [fallback_model]})
        litellm.fallbacks = existing

        # Ensure both API keys are set at module level
        litellm.api_key = settings.gemini_api_key or litellm.api_key

        # Register Groq API key via litellm's provider key dict
        if not hasattr(litellm, "_groq_api_key_set"):
            import os
            os.environ.setdefault("GROQ_API_KEY", settings.groq_api_key)

        logger.debug(
            "ChatLiteLLM module-level fallback registered",
            primary=primary_model,
            fallback=fallback_model,
        )
    else:
        logger.warning(
            "No Groq API key or fallback model configured – ChatLiteLLM has no fallback",
            primary=primary_model,
        )

    llm = ChatLiteLLM(
        model=primary_model,
        temperature=temperature,
        api_key=settings.gemini_api_key,
        max_retries=1,
    )

    return llm


