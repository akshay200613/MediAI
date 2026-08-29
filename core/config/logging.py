import logging
import sys
import warnings

import litellm
import structlog

from core.config.settings import settings


def configure_logging() -> None:
    """Configure structlog for the application."""
    # Suppress verbose third-party loggers and warnings
    litellm.suppress_debug_info = True
    litellm.set_verbose = False
    warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    noisy_loggers = (
        "litellm",
        "LiteLLM",
        "LiteLLM Router",
        "LiteLLM Proxy",
        "httpx",
        "httpcore",
        "openai",
        "langsmith",
    )

    for noisy_logger in noisy_loggers:
        logging.getLogger(noisy_logger).setLevel(logging.ERROR)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_production:
        # JSON output for production (parseable by log aggregators)
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Pretty console output for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.debug else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging to go through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.debug else logging.INFO,
    )

    # Re-apply noisy logger silence after basicConfig
    for noisy_logger in noisy_loggers:
        logging.getLogger(noisy_logger).setLevel(logging.ERROR)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a named structlog logger."""
    return structlog.get_logger(name)

