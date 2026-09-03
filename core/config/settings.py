"""
Core Configuration – Pydantic BaseSettings
All values are driven from environment variables / .env files.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    app_name: str = "MedAI"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    allowed_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    )

    # ── PostgreSQL ────────────────────────────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "medai"
    postgres_user: str = "postgres"
    postgres_password: str = "changeme"
    database_url: str = ""

    @model_validator(mode="after")
    def assemble_db_url(self) -> "Settings":
        if not self.database_url:
            self.database_url = (
                f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        return self

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_url: str = ""

    @model_validator(mode="after")
    def assemble_redis_url(self) -> "Settings":
        if not self.redis_url:
            auth = f":{self.redis_password}@" if self.redis_password else ""
            self.redis_url = f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return self

    # ── Qdrant ────────────────────────────────────────────────────────────────
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""
    qdrant_collection_prefix: str = "medai"

    # ── JWT Auth ──────────────────────────────────────────────────────────────
    jwt_secret_key: str = "insecure-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # ── Admin Bootstrap ──────────────────────────────────────────────────────
    admin_email: str = ""
    admin_password: str = ""
    admin_full_name: str = "MediAI Admin"

    # ── Email / SMTP ─────────────────────────────────────────────────────────
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "MediAI Healthcare"
    smtp_tls: bool = True
    emails_enabled: bool = False

    # ── Google AI / Gemini (Embeddings & Fallback) ─────────────────────────────
    gemini_api_key: str = ""
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_embedding_dimension: int = 768
    gemini_max_tokens: int = 8192
    gemini_temperature: float = 1.0

    # ── Groq Fallback ─────────────────────────────────────────────────────────
    groq_api_key: str = ""

    # ── LiteLLM Model Routing (Primary) ───────────────────────────────────────
    model_reception: str = "gemini/gemini-3.6-flash"
    model_medical: str = "gemini/gemini-3.6-flash"
    model_scheduling: str = "gemini/gemini-3.6-flash"
    model_knowledge: str = "gemini/gemini-3.6-flash"
    model_supervisor: str = "gemini/gemini-3.6-flash"

    # ── LiteLLM Model Routing (Fallback → Groq) ──────────────────────────────
    model_fallback_reception: str = "groq/openai/gpt-oss-20b"
    model_fallback_medical: str = "groq/openai/gpt-oss-120b"
    model_fallback_scheduling: str = "groq/openai/gpt-oss-20b"
    model_fallback_knowledge: str = "groq/openai/gpt-oss-20b"
    model_fallback_supervisor: str = "groq/openai/gpt-oss-120b"

    # ── LiteLLM Router ────────────────────────────────────────────────────────
    litellm_num_retries: int = 2
    litellm_request_timeout: int = 30
    litellm_cache_enabled: bool = True

    # ── LangSmith Observability ────────────────────────────────────────────────
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "mediai"

    # ── RAG Pipeline ─────────────────────────────────────────────────────────
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 64
    rag_top_k: int = 5
    rag_score_threshold: float = 0.35

    # ── LangGraph Agent System ────────────────────────────────────────────────
    langgraph_recursion_limit: int = 25
    langgraph_checkpoint_backend: str = "memory"  # "memory" | "redis"

    # ── Appointment Booking Limits ────────────────────────────────────────────
    max_bookings_per_slot: int = 2
    max_active_appointments_per_patient: int = 2

    # ── Computed ─────────────────────────────────────────────────────────────
    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — call this everywhere."""
    return Settings()


settings = get_settings()
