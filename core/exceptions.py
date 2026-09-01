"""
Standard Application Exception Hierarchy for MediAI.
Provides structured, typed exceptions with HTTP status codes and error response formatting.
"""

from datetime import datetime, timezone
from typing import Any


class MediAIException(Exception):
    """Base exception for all domain and platform errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_SERVER_ERROR",
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details

    def to_dict(self, request_id: str | None = None) -> dict[str, Any]:
        """Format as a standardized JSON response dict."""
        return {
            "success": False,
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
            },
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


class EntityNotFoundException(MediAIException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str, identifier: Any) -> None:
        super().__init__(
            message=f"{resource} with identifier '{identifier}' was not found.",
            status_code=404,
            error_code="NOT_FOUND",
        )


class ConflictException(MediAIException):
    """Raised when an operation creates a resource conflict (e.g. duplicate key or slot conflict)."""

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
            details=details,
        )


class ValidationException(MediAIException):
    """Raised when input validation fails."""

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class AuthenticationException(MediAIException):
    """Raised when authentication credentials are missing or invalid."""

    def __init__(self, message: str = "Invalid or expired authentication credentials.") -> None:
        super().__init__(
            message=message,
            status_code=401,
            error_code="UNAUTHORIZED",
        )


class PermissionDeniedException(MediAIException):
    """Raised when the user does not possess required permissions or roles."""

    def __init__(self, message: str = "Permission denied for this resource.") -> None:
        super().__init__(
            message=message,
            status_code=403,
            error_code="FORBIDDEN",
        )


class RateLimitException(MediAIException):
    """Raised when a rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded. Please try again later.", retry_after: int = 60) -> None:
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after},
        )


class DatabaseUnavailableException(MediAIException):
    """Raised when database connection fails or queries time out."""

    def __init__(self, message: str = "Database service is temporarily unavailable.") -> None:
        super().__init__(
            message=message,
            status_code=503,
            error_code="DATABASE_UNAVAILABLE",
        )


class AIServiceUnavailableException(MediAIException):
    """Raised when all configured LLM providers (primary + fallbacks) are unavailable."""

    def __init__(self, message: str = "The AI service is temporarily unavailable. Please try again later.") -> None:
        super().__init__(
            message=message,
            status_code=503,
            error_code="AI_SERVICE_UNAVAILABLE",
        )


class ExternalServiceTimeoutException(MediAIException):
    """Raised when an upstream external service fails to respond within the configured timeout."""

    def __init__(self, service_name: str, timeout_seconds: float) -> None:
        super().__init__(
            message=f"External service '{service_name}' timed out after {timeout_seconds}s.",
            status_code=504,
            error_code="GATEWAY_TIMEOUT",
        )
