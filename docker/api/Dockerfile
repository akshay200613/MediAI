# =============================================================================
# MediAI FastAPI Backend Dockerfile
# Production Multi-Stage, Non-Root, Minimal Attack Surface Image
# =============================================================================

# ── Stage 1: Build & Dependency Resolution ────────────────────────────────────
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy packaging metadata
COPY pyproject.toml README.md ./

# Install pip build tools and dependencies into a dedicated prefix
RUN pip install --no-cache-dir --upgrade pip setuptools wheel hatchling && \
    pip install --no-cache-dir --prefix=/install .

# ── Stage 2: Runtime Image ───────────────────────────────────────────────────
FROM python:3.11-slim-bookworm AS runtime

LABEL maintainer="MediAI Engineering <team@mediai.internal>"
LABEL description="MediAI Production Backend API Container"

WORKDIR /app

# Set production environment flags
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/app:/install/lib/python3.11/site-packages:$PYTHONPATH"

# Install minimal runtime system dependencies (libpq for postgres, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python site-packages from builder
COPY --from=builder /install /install

# Create non-root system user and group
RUN groupadd --gid 10001 appgroup && \
    useradd --uid 10001 --gid appgroup --shell /bin/bash --create-home appuser

# Copy application source code
COPY --chown=appuser:appgroup alembic.ini ./
COPY --chown=appuser:appgroup apps ./apps
COPY --chown=appuser:appgroup core ./core
COPY --chown=appuser:appgroup domains ./domains
COPY --chown=appuser:appgroup data ./data
COPY --chown=appuser:appgroup docker/api/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose FastAPI HTTP / WebSocket port
EXPOSE 8000

# Health check probe using internal liveness endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/live || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]
