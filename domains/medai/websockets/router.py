"""
WebSocket Router for MediAI.
Endpoint: /api/v1/medai/ws/appointments?token=...
Authenticates JWT, resolves user & role, and streams realtime appointment events.
"""

import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from sqlalchemy import select, or_

from core.auth.jwt_handler import decode_token
from core.database.session import AsyncSessionLocal
from core.models.user import User
from domains.medai.models.patient import Patient
from domains.medai.models.doctor import Doctor
from domains.medai.websockets.manager import manager
from core.config.logging import get_logger

logger = get_logger("medai.websockets.router")

router = APIRouter()


@router.websocket("/ws/appointments")
async def websocket_appointments(
    websocket: WebSocket,
    token: str = Query(..., description="Tab-isolated JWT access token"),
):
    """
    Authenticated WebSocket endpoint for real-time appointment notifications.
    Authenticates token query param, registers socket by user_id/role/patient_id/doctor_id,
    and streams realtime updates to connected client portals.
    """
    socket_id = str(uuid.uuid4())

    # 1. Authenticate Token
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role", "user")

        if not user_id or not email:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception as exc:
        logger.warning("WebSocket authentication failed", error=str(exc))
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Resolve Linked Patient ID / Doctor ID
    patient_id = None
    doctor_id = None

    async with AsyncSessionLocal() as session:
        # Check Patient
        pat_res = await session.execute(
            select(Patient).where(
                or_(Patient.user_id == user_id, Patient.email == email),
                Patient.is_deleted == False,
            )
        )
        pat = pat_res.scalar_one_or_none()
        if pat:
            patient_id = str(pat.id)

        # Check Doctor
        doc_res = await session.execute(
            select(Doctor).where(
                or_(Doctor.user_id == user_id, Doctor.email == email),
                Doctor.is_deleted == False,
            )
        )
        doc = doc_res.scalar_one_or_none()
        if doc:
            doctor_id = str(doc.id)

    # 3. Register Connection
    await manager.connect(
        websocket=websocket,
        socket_id=socket_id,
        user_id=user_id,
        role=role,
        patient_id=patient_id,
        doctor_id=doctor_id,
    )

    try:
        while True:
            # Receive ping/pong keep-alive or client messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(socket_id)
    except Exception as exc:
        logger.warning("WebSocket error", socket_id=socket_id, error=str(exc))
        manager.disconnect(socket_id)
