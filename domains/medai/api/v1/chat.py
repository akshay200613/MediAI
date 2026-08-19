"""
AI Chat API Endpoint – /api/v1/medai/chat
Supports regular and streaming responses from the Medical AI Agent.
"""

import uuid
import json
import logging
from typing import AsyncIterator
from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_db
from core.auth.dependencies import get_current_user, CurrentUser
from core.auth.permissions import require_permission, Permission
from core.schemas.base import DataResponse
from domains.medai.schemas.chat import ChatMessage, ChatResponse
from core.ai.llm.litellm_client import get_llm_client
from core.ai.conversation.session_manager import SessionManager
from core.ai.llm.client import Message
from core.models.user import User
from domains.medai.models.patient import Patient

logger = logging.getLogger("medai.chat_api")

router = APIRouter()

def has_patient_details(message: str) -> bool:
    """Check whether the message contains patient profile information."""
    keywords = (
        "date of birth",
        "dob",
        "gender",
        "blood group",
        "blood type",
        "address",
        "city",
        "state",
        "emergency contact",
    )

    message_lower = message.lower()
    return any(keyword in message_lower for keyword in keywords)

async def extract_and_update_patient(user_message: str, user_id: str, email: str, session: AsyncSession) -> dict:
    """
    Extract patient details from user message and update patient record.
    Returns a dict of updated fields.
    """
    if not has_patient_details(user_message):
        return {}

    # Get or create patient record
    pat_res = await session.execute(
        select(Patient).where(
            (Patient.email == email) | (Patient.user_id == str(user_id)),
            Patient.is_deleted == False
        )
    )
    pat = pat_res.scalar_one_or_none()
    
    if not pat:
        user_res = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = user_res.scalar_one_or_none()
        full_name = user.full_name if user else email
        parts = full_name.split(" ", 1)
        pat = Patient(
            user_id=str(user_id),
            first_name=parts[0],
            last_name=parts[1] if len(parts) > 1 else "",
            email=email,
            phone="000-000-0000",
        )
        session.add(pat)
        await session.flush()

    prompt = f"""
    You are a precise data extractor. Analyze the user's message and extract any patient personal details.
    
    User Message: "{user_message}"
    
    Extract the following fields if present:
    - date_of_birth: Date in YYYY-MM-DD format (if they mention date of birth)
    - gender: One of "male", "female", "other"
    - blood_group: One of "A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"
    - address: Street address
    - city: City
    - state: State
    - emergency_contact_name: Full name of emergency contact
    - emergency_contact_phone: Phone number of emergency contact

    Return ONLY a valid JSON object. Do not include any markdown, block quotes, backticks, or explanation.
    Example output format:
    {{"date_of_birth": "1990-05-15", "gender": "male"}}
    
    If no fields are found, return an empty JSON object {{}}.
    """
    
    try:
        llm = get_llm_client()
        response = await llm.generate(
            messages=[Message(role="user", content=prompt)],
            temperature=1.0,
            max_tokens=500,
        )
        content = response.content.strip()
        
        # Clean markdown codeblocks if LLM outputs them
        if content.startswith("```"):
            lines = content.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()
            
        data = json.loads(content)
        
        updated_fields = {}
        if not isinstance(data, dict):
            return updated_fields

        # Apply updates to pat
        if "date_of_birth" in data and data["date_of_birth"]:
            try:
                pat.date_of_birth = date.fromisoformat(data["date_of_birth"].split("T")[0])
                updated_fields["date_of_birth"] = data["date_of_birth"]
            except Exception:
                pass
        if "gender" in data and data["gender"]:
            normalized_gender = data["gender"].lower().strip()
            if normalized_gender in ("male", "female", "other"):
                pat.gender = normalized_gender
                updated_fields["gender"] = normalized_gender
        if "blood_group" in data and data["blood_group"]:
            pat.blood_group = data["blood_group"]
            updated_fields["blood_group"] = data["blood_group"]
        if "address" in data and data["address"]:
            pat.address = data["address"]
            updated_fields["address"] = data["address"]
        if "city" in data and data["city"]:
            pat.city = data["city"]
            updated_fields["city"] = data["city"]
        if "state" in data and data["state"]:
            pat.state = data["state"]
            updated_fields["state"] = data["state"]
        if "emergency_contact_name" in data and data["emergency_contact_name"]:
            pat.emergency_contact_name = data["emergency_contact_name"]
            updated_fields["emergency_contact_name"] = data["emergency_contact_name"]
        if "emergency_contact_phone" in data and data["emergency_contact_phone"]:
            pat.emergency_contact_phone = data["emergency_contact_phone"]
            updated_fields["emergency_contact_phone"] = data["emergency_contact_phone"]

        if updated_fields:
            await session.commit()
            logger.info(f"Updated patient {pat.id} details via chatbot: {updated_fields}")
            
        return updated_fields
    except Exception as exc:
        logger.error(f"Failed to extract patient info from message: {exc}")
        return {}


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
    session_mgr = SessionManager(session)

    # Fast-path for simple small talk (bypasses LLM and LangGraph completely)
    import re
    user_msg_lower = message.content.strip().lower()
    # Remove punctuation for matching
    clean_msg = re.sub(r'[^\w\s]', '', user_msg_lower).strip()
    
    small_talk_greetings = {"hi", "hello", "hey", "good morning", "good evening", "good afternoon"}
    small_talk_thanks = {"thanks", "thank you", "thank u", "thx"}
    
    if clean_msg in small_talk_greetings:
        reply = "Hello! I am MedAI, your intelligent clinic assistant. How can I assist you with medical questions, appointment scheduling, or hospital information today?"
        await session_mgr.add_exchange(current_user.user_id, session_id, message.content, reply)
        return DataResponse(
            data=ChatResponse(
                content=reply,
                session_id=session_id,
                sources=[],
                agent_name="supervisor",
                tool_calls=[],
            ),
            message="Chat processed successfully",
        )
    elif clean_msg in small_talk_thanks:
        reply = "You're very welcome! Let me know if you need any further assistance."
        await session_mgr.add_exchange(current_user.user_id, session_id, message.content, reply)
        return DataResponse(
            data=ChatResponse(
                content=reply,
                session_id=session_id,
                sources=[],
                agent_name="supervisor",
                tool_calls=[],
            ),
            message="Chat processed successfully",
        )

    # Load conversation history for current session
    history = await session_mgr.get_last_n_messages(current_user.user_id, session_id, n=10)
    
    # Load cross-session memory for the patient
    long_term_memory = await session_mgr.get_recent_history_cross_session(current_user.user_id, n=20)

    # Extract and update patient details if user is patient
    updated_fields = {}
    missing_fields = []
    patient_name = current_user.full_name

    if current_user.role in ("patient", "user"):
        updated_fields = await extract_and_update_patient(
            user_message=message.content,
            user_id=current_user.user_id,
            email=current_user.email,
            session=session,
        )
        
        # Check missing fields
        pat_res = await session.execute(
            select(Patient).where(
                (Patient.email == current_user.email) | (Patient.user_id == str(current_user.user_id)),
                Patient.is_deleted == False
            )
        )
        pat = pat_res.scalar_one_or_none()
        if pat:
            patient_name = pat.full_name
            if not pat.date_of_birth:
                missing_fields.append("Date of Birth")
            if not pat.gender:
                missing_fields.append("Gender")
            if not pat.blood_group:
                missing_fields.append("Blood Group")
            if not pat.address:
                missing_fields.append("Street Address")
            if not pat.emergency_contact_name:
                missing_fields.append("Emergency Contact Name")
            if not pat.emergency_contact_phone:
                missing_fields.append("Emergency Contact Phone")

    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from core.ai.graph.builder import build_medai_graph

    # Map history to Langchain messages
    langchain_messages = []
    
    # Inject long-term memory summary as a system message
    if long_term_memory:
        memory_str = "\n".join([f"{m.role}: {m.content}" for m in long_term_memory])
        langchain_messages.append(SystemMessage(content=f"[System Note: Patient's recent conversation history across past sessions (Long-Term Memory):\n{memory_str}\n]"))
        
    for msg in history:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        else:
            langchain_messages.append(AIMessage(content=msg.content))
            
    # Inject missing fields instruction as a system message if needed
    if missing_fields:
        missing_str = ", ".join(missing_fields)
        langchain_messages.append(SystemMessage(content=f"[System Note: Patient profile is missing {missing_str}. Please politely ask for these details.]"))

    langchain_messages.append(HumanMessage(content=message.content))

    patient_context = {}
    if pat:
        patient_context = {
            "first_name": pat.first_name,
            "last_name": pat.last_name,
            "email": pat.email,
            "phone": pat.phone,
            "date_of_birth": pat.date_of_birth.isoformat() if pat.date_of_birth else None,
            "gender": pat.gender,
            "blood_group": pat.blood_group,
            "address": pat.address,
        }

    graph = build_medai_graph()
    state = {
        "messages": langchain_messages,
        "user_id": current_user.user_id,
        "session_id": session_id,
        "patient_context": patient_context,
        "metadata": {
            "patient_id": message.patient_id,
            "use_rag": message.use_rag,
            "updated_fields": updated_fields,
            "missing_fields": missing_fields,
            "patient_name": patient_name,
        }
    }
    
    config = {"configurable": {"thread_id": session_id}}
    result = await graph.ainvoke(state, config=config)
    
    final_response_text = result.get("final_response")
    if not final_response_text and result.get("messages"):
        content = result["messages"][-1].content
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, str):
                    text_parts.append(part)
                elif isinstance(part, dict) and "text" in part:
                    text_parts.append(part["text"])
            final_response_text = "\n".join(text_parts)
        elif isinstance(content, str):
            final_response_text = content
        else:
            final_response_text = str(content)
            
    if not isinstance(final_response_text, str):
        final_response_text = str(final_response_text or "")
        
    # Safely handle tool calls extraction from the last AIMessage if present
    tool_calls = []
    if result.get("messages") and hasattr(result["messages"][-1], "tool_calls"):
        tool_calls = result["messages"][-1].tool_calls
        
    final_response_text = final_response_text.strip()
    if not final_response_text:
        if tool_calls:
            names = [tc.get("name", "action") for tc in tool_calls]
            final_response_text = f"I am executing the following tasks: {', '.join(names)}."
        else:
            final_response_text = "I have processed your request."

    # Persist exchange
    await session_mgr.add_exchange(current_user.user_id, session_id, message.content, final_response_text)

    return DataResponse(
        data=ChatResponse(
            content=final_response_text,
            session_id=session_id,
            sources=[],
            agent_name=result.get("current_agent", "supervisor"),
            tool_calls=tool_calls,
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
    session: AsyncSession = Depends(get_db),
) -> None:
    """Clear the conversation history for a session."""
    session_mgr = SessionManager(session)
    await session_mgr.clear(current_user.user_id, session_id)


@router.get(
    "/sessions",
    summary="Get patient chat sessions",
)
async def get_sessions(
    current_user: CurrentUser = Depends(require_permission(Permission.USE_AI_CHAT)),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve all chat sessions for the current patient."""
    from domains.medai.models.chat_history import ChatSession
    
    stmt = (
        select(ChatSession)
        .where(ChatSession.user_id == current_user.user_id)
        .order_by(ChatSession.updated_at.desc())
    )
    result = await session.execute(stmt)
    sessions = result.scalars().all()
    
    return DataResponse(
        data=[{"id": s.id, "title": s.title, "updated_at": s.updated_at} for s in sessions],
        message="Fetched chat sessions successfully",
    )


@router.get(
    "/sessions/{session_id}/messages",
    summary="Get messages for a chat session",
)
async def get_session_messages(
    session_id: str,
    current_user: CurrentUser = Depends(require_permission(Permission.USE_AI_CHAT)),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve all messages for a specific session."""
    from domains.medai.models.chat_history import ChatSession, ChatMessage
    
    # Verify session belongs to user
    stmt_sess = select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == current_user.user_id)
    result_sess = await session.execute(stmt_sess)
    chat_session = result_sess.scalar_one_or_none()
    
    if not chat_session:
        return DataResponse(success=False, message="Session not found or unauthorized", data=[])
        
    stmt_msg = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    result_msg = await session.execute(stmt_msg)
    messages = result_msg.scalars().all()
    
    return DataResponse(
        data=[{"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at} for m in messages],
        message="Fetched messages successfully",
    )
