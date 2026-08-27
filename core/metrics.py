"""
MediAI Metrics Module – Prometheus instrumentation.

Exposes a /metrics endpoint and tracks:
  - HTTP request counts / latency (via prometheus-fastapi-instrumentator)
  - Active WebSocket connections
  - AI chat requests (by role)
  - Appointment bookings (success / conflict)
  - AI service errors (503)
  - RAG query counts
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

# ── AI Chat ───────────────────────────────────────────────────────────────────

chat_requests_total = Counter(
    "medai_chat_requests_total",
    "Total number of AI chat requests",
    ["role", "path_type"],  # path_type: small_talk | medical_query
)

chat_errors_total = Counter(
    "medai_chat_errors_total",
    "Total number of AI chat errors (503s)",
    ["error_type"],  # ai_unavailable | graph_exception
)

chat_latency_seconds = Histogram(
    "medai_chat_latency_seconds",
    "End-to-end latency of AI chat requests (seconds)",
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
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

rag_queries_total = Counter(
    "medai_rag_queries_total",
    "Total RAG knowledge base queries",
    ["role"],
)

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
