"""
AI Chat schemas for MedAI.
"""

from typing import Optional
from pydantic import Field
from core.schemas.base import BaseSchema


class ChatMessage(BaseSchema):
    content: str = Field(min_length=1, max_length=4000)
    session_id: Optional[str] = None
    patient_id: Optional[str] = None   # Optional patient context
    use_rag: bool = True                # Whether to use knowledge base retrieval


class ChatResponse(BaseSchema):
    content: str
    session_id: str
    sources: list[dict] = []
    agent_name: str = "medical_agent"
    tool_calls: list[dict] = []
