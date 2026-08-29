"""Platform-wide constants."""

from enum import StrEnum


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class UserRole(StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    # Domain-specific roles extend this via domain registries
    USER = "user"


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class NotificationChannel(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


# Pagination defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Cache TTLs (seconds)
CACHE_TTL_SHORT = 60          # 1 minute
CACHE_TTL_MEDIUM = 300        # 5 minutes
CACHE_TTL_LONG = 3600         # 1 hour
CACHE_TTL_DAY = 86400         # 24 hours

# Session
SESSION_TTL = 86400           # 24 hours

# AI
AI_MAX_RETRIES = 3
AI_RETRY_DELAY = 1.0          # seconds
AI_CONTEXT_WINDOW = 128000    # Gemini 2.5 Flash context window

# File uploads
MAX_FILE_SIZE_MB = 50
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg"}

# API versioning
API_V1_PREFIX = "/api/v1"
API_V2_PREFIX = "/api/v2"

# Appointment Booking Limits
MAX_BOOKINGS_PER_SLOT = 2
MAX_ACTIVE_APPOINTMENTS_PER_PATIENT = 2

