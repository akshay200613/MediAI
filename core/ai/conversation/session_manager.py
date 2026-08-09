"""
Session Manager – stores and retrieves conversation history using Redis.
"""

import json
from typing import Any

from core.ai.llm.client import Message
from core.database.redis_client import get_redis
from core.config.logging import get_logger

logger = get_logger(__name__)

SESSION_PREFIX = "medai:chat:session:"
SESSION_TTL = 86400  # 24 hours


class SessionManager:
    """Manages chat session history in Redis."""

    async def get_last_n_messages(self, session_id: str, *, n: int = 10) -> list[Message]:
        """Retrieve the last N messages from a session."""
        redis = get_redis()
        key = f"{SESSION_PREFIX}{session_id}"
        try:
            raw_messages = await redis.lrange(key, -n, -1)
            messages = []
            for raw in raw_messages:
                data = json.loads(raw)
                messages.append(Message(role=data["role"], content=data["content"]))
            return messages
        except Exception as e:
            logger.warning("Failed to retrieve session history", session_id=session_id, error=str(e))
            return []

    async def add_exchange(self, session_id: str, user_message: str, assistant_message: str) -> None:
        """Persist a user/assistant exchange to the session."""
        redis = get_redis()
        key = f"{SESSION_PREFIX}{session_id}"
        try:
            await redis.rpush(
                key,
                json.dumps({"role": "user", "content": user_message}),
                json.dumps({"role": "assistant", "content": assistant_message}),
            )
            await redis.expire(key, SESSION_TTL)
        except Exception as e:
            logger.warning("Failed to persist exchange", session_id=session_id, error=str(e))

    async def clear(self, session_id: str) -> None:
        """Clear all messages for a session."""
        redis = get_redis()
        key = f"{SESSION_PREFIX}{session_id}"
        try:
            await redis.delete(key)
        except Exception as e:
            logger.warning("Failed to clear session", session_id=session_id, error=str(e))
