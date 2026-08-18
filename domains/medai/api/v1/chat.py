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
import asyncio

from core.database.session import get_db
from core.auth.dependencies import get_current_user, CurrentUser
from core.auth.permissions import require_permission, Permission
from core.schemas.base import DataResponse
from domains.medai.schemas.chat import ChatMessage, ChatResponse
from core.ai.llm.gemini_client import get_llm_client
from core.ai.conversation.session_manager import SessionManager
from core.ai.llm.client import Message
from core.models.user import User
from domains.medai.models.patient import Patient

logger = logging.getLogger("medai.chat_api")

router = APIRouter()


async def extract_and_update_patient(user_message: str, user_id: str, email: str, session: AsyncSession) -> dict:
    """
    Extract patient details from user message and update patient record.
    Returns a dict of updated fields.
    """
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
            temperature=0.0,
            max_tokens=150,
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
    session_mgr = SessionManager()

    # Load conversation history
    history = await session_mgr.get_last_n_messages(current_user.user_id, session_id, n=10)

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
        final_response_text = result["messages"][-1].content
    
    # Safely handle tool calls extraction from the last AIMessage if present
    tool_calls = []
    if result.get("messages") and hasattr(result["messages"][-1], "tool_calls"):
        tool_calls = result["messages"][-1].tool_calls

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


@router.post(
    "/stream",
    response_class=StreamingResponse,
    summary="Stream Chat with Medical AI Agent",
)
async def chat_stream(
    message: ChatMessage,
    current_user: CurrentUser = Depends(require_permission(Permission.USE_AI_CHAT)),
    session: AsyncSession = Depends(get_db),
):
    session_id = message.session_id or str(uuid.uuid4())
    session_mgr = SessionManager()

    # Load conversation history
    history = await session_mgr.get_last_n_messages(current_user.user_id, session_id, n=10)

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
    for msg in history:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        else:
            langchain_messages.append(AIMessage(content=msg.content))
            
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

    async def event_generator():
        final_content = ""
        try:
            async for event in graph.astream_events(state, config=config, version="v2"):
                if event["event"] == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        content_str = str(chunk.content)
                        final_content += content_str
                        yield f"data: {json.dumps({'content': content_str})}\n\n"
            
            # Persist after generation completes
            await session_mgr.add_exchange(current_user.user_id, session_id, message.content, final_content)
        except asyncio.CancelledError:
            # Client disconnected
            pass
        except Exception as e:
            logger.error(f"Error during streaming: {e}")
            yield f"data: {json.dumps({'error': 'An error occurred during generation'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
    await session_mgr.clear(current_user.user_id, session_id)
