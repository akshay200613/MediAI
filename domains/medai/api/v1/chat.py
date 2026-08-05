"""
AI Chat API Endpoint – /api/v1/medai/chat
Supports regular and streaming responses from the Medical AI Agent.
"""

import uuid
from typing import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_db
from core.auth.dependencies import get_current_user, CurrentUser
from core.auth.permissions import require_permission, Permission
from core.schemas.base import DataResponse
from domains.medai.schemas.chat import ChatMessage, ChatResponse
from domains.medai.ai.agents.medical_agent import MedicalAgent
from core.ai.llm.gemini_client import get_llm_client
from core.ai.conversation.session_manager import SessionManager
from core.ai.agents.base_agent import AgentContext
from core.ai.llm.client import Message

router = APIRouter()


@router.post(
    "",
    response_model=DataResponse[ChatResponse],
    summary="Chat with Medical AI Agent",
)
async def chat(
    message: ChatMessage,
    current_user: CurrentUser = Depends(require_permission(Permission.USE_AI_CHAT)),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ChatResponse]:
    session_id = message.session_id or str(uuid.uuid4())
    session_mgr = SessionManager()

    # Load conversation history
    history = await session_mgr.get_last_n_messages(session_id, n=10)

    # Build agent context
    context = AgentContext(
        session_id=session_id,
        user_id=current_user.user_id,
        domain="medai",
        messages=history + [Message(role="user", content=message.content)],
        metadata={
            "patient_id": message.patient_id,
            "use_rag": message.use_rag,
        },
    )

    # Run Medical AI Agent
    agent = MedicalAgent(llm_client=get_llm_client())
    response = await agent.invoke(context)

    # Persist exchange
    await session_mgr.add_exchange(session_id, message.content, response.content)

    return DataResponse(
        data=ChatResponse(
            content=response.content,
            session_id=session_id,
            sources=response.sources,
            agent_name=response.agent_name,
            tool_calls=response.tool_calls,
        ),
        message="Response generated",
    )


@router.delete(
    "/sessions/{session_id}",
    status_code=204,
    summary="Clear a chat session",
)
async def clear_session(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    """Clear the conversation history for a session."""
    session_mgr = SessionManager()
    await session_mgr.clear(session_id)
