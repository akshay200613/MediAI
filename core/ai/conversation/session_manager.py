"""
Session Manager – stores and retrieves conversation history using Redis.
"""

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.ai.llm.client import Message
from domains.medai.models.chat_history import ChatSession, ChatMessage
from core.config.logging import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Manages chat session history in PostgreSQL, isolated per user."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_last_n_messages(self, user_id: str, session_id: str, *, n: int = 10) -> list[Message]:
        """Retrieve the last N messages from a specific session."""
        try:
            stmt = (
                select(ChatMessage)
                .join(ChatSession)
                .where(ChatSession.user_id == user_id, ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(n)
            )
            result = await self.db.execute(stmt)
            raw_messages = result.scalars().all()
            
            # They come out descending, so reverse to chronological
            messages = []
            for msg in reversed(raw_messages):
                messages.append(Message(role=msg.role, content=msg.content))
            return messages
        except Exception as e:
            logger.warning("Failed to retrieve session history", session_id=session_id, user_id=user_id, error=str(e))
            return []

    async def get_recent_history_cross_session(self, user_id: str, *, n: int = 20) -> list[Message]:
        """Retrieve the last N messages for a user across ALL their sessions."""
        try:
            stmt = (
                select(ChatMessage)
                .join(ChatSession)
                .where(ChatSession.user_id == user_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(n)
            )
            result = await self.db.execute(stmt)
            raw_messages = result.scalars().all()
            
            messages = []
            for msg in reversed(raw_messages):
                messages.append(Message(role=msg.role, content=msg.content))
            return messages
        except Exception as e:
            logger.warning("Failed to retrieve cross-session history", user_id=user_id, error=str(e))
            return []

    async def add_exchange(self, user_id: str, session_id: str, user_message: str, assistant_message: str, title: str = "New Consultation") -> None:
        """Persist a user/assistant exchange to the session."""
        try:
            # Check if session exists
            stmt = select(ChatSession).where(ChatSession.id == session_id)
            result = await self.db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if not session:
                session = ChatSession(id=session_id, user_id=user_id, title=title)
                self.db.add(session)
                
            # Add messages
            user_msg = ChatMessage(session_id=session_id, role="user", content=user_message)
            assistant_msg = ChatMessage(session_id=session_id, role="assistant", content=assistant_message)
            
            self.db.add(user_msg)
            self.db.add(assistant_msg)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.warning("Failed to persist exchange", session_id=session_id, user_id=user_id, error=str(e))

    async def clear(self, user_id: str, session_id: str) -> None:
        """Clear all messages for a session (by deleting the session)."""
        try:
            stmt = select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            result = await self.db.execute(stmt)
            session = result.scalar_one_or_none()
            if session:
                await self.db.delete(session)
                await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.warning("Failed to clear session", session_id=session_id, user_id=user_id, error=str(e))
