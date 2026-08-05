"""
Conversation Session Manager – Redis-backed session store.
Manages per-user, per-session chat history and context.
"""

import json
from datetime import datetime, timezone

from core.database.redis_client import get_redis
from core.ai.llm.client import Message
from core.config.constants import SESSION_TTL
from core.config.logging import get_logger

logger = get_logger(__name__)


class SessionManager:
    """
    Manages conversation sessions stored in Redis.
    Each session has a unique ID and stores message history.
    """

    KEY_PREFIX = "session"

    def __init__(self) -> None:
        self.redis = get_redis()

    def _key(self, session_id: str) -> str:
        return f"{self.KEY_PREFIX}:{session_id}"

    async def get_history(self, session_id: str) -> list[Message]:
        """Retrieve message history for a session."""
        raw = await self.redis.get(self._key(session_id))
        if not raw:
            return []
        data = json.loads(raw)
        return [Message(role=m["role"], content=m["content"]) for m in data.get("messages", [])]

    async def append_message(self, session_id: str, message: Message) -> None:
        """Append a message to the session history."""
        history = await self.get_history(session_id)
        history.append(message)
        await self._save(session_id, history)

    async def add_exchange(
        self, session_id: str, user_message: str, assistant_message: str
    ) -> None:
        """Add a complete user/assistant exchange to history."""
        history = await self.get_history(session_id)
        history.append(Message(role="user", content=user_message))
        history.append(Message(role="assistant", content=assistant_message))
        await self._save(session_id, history)

    async def clear(self, session_id: str) -> None:
        """Clear session history."""
        await self.redis.delete(self._key(session_id))
        logger.info("Session cleared", session_id=session_id)

    async def _save(self, session_id: str, messages: list[Message]) -> None:
        """Persist session to Redis with TTL."""
        data = {
            "session_id": session_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        await self.redis.setex(
            self._key(session_id),
            SESSION_TTL,
            json.dumps(data),
        )

    async def get_last_n_messages(self, session_id: str, n: int = 10) -> list[Message]:
        """Get the last N messages from history (for context window management)."""
        history = await self.get_history(session_id)
        return history[-n:]
