"""
MediAI Metrics Module – Prometheus instrumentation.

Exposes a /metrics endpoint and tracks:
  - HTTP request counts / latency (via prometheus-fastapi-instrumentator)
  - Active WebSocket connections
  - AI chat requests & LLM latency, tokens, cost, and fallback failovers
  - Appointment bookings (success / conflict / error)
  - Authentication attempts
  - RAG document ingestion & indexing
  - Exception and Redis operational metrics
"""

from prometheus_client import Counter, Gauge, Histogram, Info
from prometheus_fastapi_instrumentator import Instrumentator, metrics

# ── Application Info ──────────────────────────────────────────────────────────

app_info = Info(
    "medai_app",
    "MedAI application metadata",
)

# ── WebSocket Connections ────────────────────────────────────────────────────

ws_connections_active = Gauge(
    "medai_websocket_connections_active",
    "Number of currently active WebSocket connections",
    ["role"],
)

# ── Appointments ──────────────────────────────────────────────────────────────

appointment_bookings_total = Counter(
    "medai_appointment_bookings_total",
    "Total appointment booking attempts",
    ["outcome"],  # success | conflict | error
)

appointment_cancellations_total = Counter(
    "medai_appointment_cancellations_total",
    "Total appointment cancellations",
    ["role"],
)

# ── RAG Pipeline ──────────────────────────────────────────────────────────────

rag_ingest_total = Counter(
    "medai_rag_ingest_total",
    "Total RAG document ingestions",
    ["outcome"],  # success | error
)

rag_chunks_indexed = Histogram(
    "medai_rag_chunks_indexed",
    "Number of chunks indexed per document ingestion",
    buckets=[1, 5, 10, 25, 50, 100, 250],
)

# ── Authentication ────────────────────────────────────────────────────────────

auth_login_total = Counter(
    "medai_auth_login_total",
    "Total login attempts",
    ["outcome"],  # success | wrong_password | unknown_user | disabled
)

# ── LLM Observability & Latency / Tokens / Cost / Fallback ───────────────────

llm_requests_total = Counter(
    "medai_llm_requests_total",
    "Total LLM generation requests",
    ["model", "outcome", "fallback_used"],  # outcome: success | error | fallback
)

llm_request_duration_seconds = Histogram(
    "medai_llm_request_duration_seconds",
    "Latency of LLM completion calls in seconds",
    ["model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 3.5, 5.0, 10.0, 15.0, 30.0],
)

llm_tokens_total = Counter(
    "medai_llm_tokens_total",
    "Total prompt and completion tokens processed by LLMs",
    ["model", "token_type"],  # token_type: prompt | completion
)

llm_cost_estimated_dollars = Counter(
    "medai_llm_cost_estimated_dollars",
    "Estimated dollar cost of LLM tokens consumed",
    ["model"],
)

llm_fallbacks_total = Counter(
    "medai_llm_fallbacks_total",
    "Total failover events from primary model to fallback model",
    ["from_model", "to_model"],
)

# ── Redis & Exceptions ───────────────────────────────────────────────────────

redis_operations_total = Counter(
    "medai_redis_operations_total",
    "Total Redis cache, rate-limit, or state operations",
    ["operation", "status"],  # status: success | error | fallback
)

exceptions_total = Counter(
    "medai_exceptions_total",
    "Total HTTP and background exceptions encountered",
    ["exception_type", "status_code"],
)


def init_metrics() -> None:
    """Initialize custom metric series with default values so Prometheus exposes them immediately on startup."""
    for role in ("patient", "doctor", "admin", "user"):
        ws_connections_active.labels(role=role).set(0)
        appointment_cancellations_total.labels(role=role).inc(0)

    for outcome in ("success", "conflict", "error"):
        appointment_bookings_total.labels(outcome=outcome).inc(0)

    for outcome in ("success", "wrong_password", "unknown_user", "disabled"):
        auth_login_total.labels(outcome=outcome).inc(0)

    for outcome in ("success", "error"):
        rag_ingest_total.labels(outcome=outcome).inc(0)

    for outcome in ("success", "error"):
        for fallback in ("true", "false"):
            llm_requests_total.labels(model="gemini/gemini-2.5-flash", outcome=outcome, fallback_used=fallback).inc(0)

    for ttype in ("prompt", "completion"):
        llm_tokens_total.labels(model="gemini/gemini-2.5-flash", token_type=ttype).inc(0)


# ── Instrumentator Factory ────────────────────────────────────────────────────

def create_instrumentator() -> Instrumentator:
    """
    Build a prometheus-fastapi-instrumentator that adds:
      - Default HTTP metrics (request count, latency, status codes)
      - Custom MedAI metrics via add() calls
    """
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/docs", "/redoc", "/openapi.json", "/metrics", "/favicon.ico"],
        inprogress_name="medai_http_requests_inprogress",
        inprogress_labels=True,
    )

    # Default metrics: latency + request count
    instrumentator.add(
        metrics.latency(
            metric_name="medai_http_request_duration_seconds",
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )
    )
    instrumentator.add(
        metrics.requests(
            metric_name="medai_http_requests_total",
        )
    )

    return instrumentator
