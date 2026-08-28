"""
WebSocket Connection Manager for MediAI.
Manages tab-isolated WebSocket connections grouped by user_id, role, patient_id, and doctor_id.
"""

from collections import defaultdict
from typing import Any
from fastapi import WebSocket
from core.config.logging import get_logger
from core.metrics import ws_connections_active

logger = get_logger("medai.websockets.manager")


class ConnectionManager:
    def __init__(self) -> None:
        # socket_id -> WebSocket
        self.active_connections: dict[str, WebSocket] = {}
        # metadata mapping: socket_id -> dict
        self.socket_meta: dict[str, dict[str, Any]] = {}
        # user_id -> set of socket_ids
        self.user_sockets: dict[str, set[str]] = defaultdict(set)
        # role -> set of socket_ids
        self.role_sockets: dict[str, set[str]] = defaultdict(set)
        # patient_id -> set of socket_ids
        self.patient_sockets: dict[str, set[str]] = defaultdict(set)
        # doctor_id -> set of socket_ids
        self.doctor_sockets: dict[str, set[str]] = defaultdict(set)

    async def connect(
        self,
        websocket: WebSocket,
        socket_id: str,
        user_id: str,
        role: str,
        patient_id: str | None = None,
        doctor_id: str | None = None,
    ) -> None:
        await websocket.accept()
        self.active_connections[socket_id] = websocket
        self.socket_meta[socket_id] = {
            "user_id": user_id,
            "role": role,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
        }

        self.user_sockets[user_id].add(socket_id)
        self.role_sockets[role].add(socket_id)

        if patient_id:
            self.patient_sockets[patient_id].add(socket_id)
        if doctor_id:
            self.doctor_sockets[doctor_id].add(socket_id)

        ws_connections_active.labels(role=role).inc()
        logger.info(
            "WebSocket connected",
            socket_id=socket_id,
            user_id=user_id,
            role=role,
            patient_id=patient_id,
            doctor_id=doctor_id,
        )

    def disconnect(self, socket_id: str) -> None:
        if socket_id in self.active_connections:
            meta = self.socket_meta.get(socket_id, {})
            user_id = meta.get("user_id")
            role = meta.get("role")
            patient_id = meta.get("patient_id")
            doctor_id = meta.get("doctor_id")

            del self.active_connections[socket_id]
            if socket_id in self.socket_meta:
                del self.socket_meta[socket_id]

            if user_id and socket_id in self.user_sockets[user_id]:
                self.user_sockets[user_id].remove(socket_id)
            if role and socket_id in self.role_sockets[role]:
                self.role_sockets[role].remove(socket_id)
            if patient_id and socket_id in self.patient_sockets.get(patient_id, set()):
                self.patient_sockets[patient_id].remove(socket_id)
            if doctor_id and socket_id in self.doctor_sockets.get(doctor_id, set()):
                self.doctor_sockets[doctor_id].remove(socket_id)

            if role:
                ws_connections_active.labels(role=role).dec()
            logger.info("WebSocket disconnected", socket_id=socket_id, user_id=user_id)

    async def broadcast_event(self, payload: dict[str, Any], socket_ids: set[str]) -> None:
        """Broadcast a JSON payload to a specific set of active socket_ids."""
        disconnected = []
        for sid in list(socket_ids):
            ws = self.active_connections.get(sid)
            if ws:
                try:
                    await ws.send_json(payload)
                except Exception as e:
                    logger.warning("Failed to send WebSocket message", socket_id=sid, error=str(e))
                    disconnected.append(sid)
            else:
                disconnected.append(sid)

        for sid in disconnected:
            self.disconnect(sid)

    async def notify_appointment_event(
        self,
        event_type: str,  # "appointment_created" | "appointment_updated" | "appointment_cancelled"
        appointment_data: dict[str, Any],
        patient_id: str | None = None,
        doctor_id: str | None = None,
    ) -> None:
        """
        Notify all connected portals (patients, doctors, admins) so slot availability,
        master appointment matrix, doctor calendar, and patient history update in real time.
        """
        payload = {
            "event": event_type,
            "data": appointment_data,
        }

        # Notify admins, super_admins, all doctors, and the target patient
        target_sockets: set[str] = set()
        target_sockets.update(self.role_sockets.get("admin", set()))
        target_sockets.update(self.role_sockets.get("super_admin", set()))
        target_sockets.update(self.role_sockets.get("doctor", set()))
        if patient_id:
            pid_str = str(patient_id)
            if pid_str in self.patient_sockets:
                target_sockets.update(self.patient_sockets[pid_str])
            if pid_str in self.user_sockets:
                target_sockets.update(self.user_sockets[pid_str])
        if doctor_id:
            did_str = str(doctor_id)
            if did_str in self.doctor_sockets:
                target_sockets.update(self.doctor_sockets[did_str])
            if did_str in self.user_sockets:
                target_sockets.update(self.user_sockets[did_str])

        await self.broadcast_event(payload, target_sockets)

    async def notify_doctor_updated(
        self,
        doctor_id: str,
        doctor_data: dict[str, Any],
        changes_summary: str | None = None,
    ) -> None:
        """
        Notify target doctor and admins when admin edits doctor profile.
        """
        payload = {
            "event": "doctor_updated",
            "message": changes_summary or "Admin has updated your profile details.",
            "data": doctor_data,
        }

        target_sockets: set[str] = set()
        target_sockets.update(self.role_sockets.get("admin", set()))
        target_sockets.update(self.role_sockets.get("super_admin", set()))
        target_sockets.update(self.role_sockets.get("doctor", set()))

        if doctor_id in self.doctor_sockets:
            target_sockets.update(self.doctor_sockets[doctor_id])

        logger.info(
            "Broadcasting doctor_updated event",
            doctor_id=doctor_id,
            recipient_sockets_count=len(target_sockets),
        )

        await self.broadcast_event(payload, target_sockets)

    async def notify_admin_password_reset_request(
        self,
        user_id: str,
        email: str,
        full_name: str,
    ) -> None:
        """
        Notify all admins when a doctor requests a password reset.
        """
        payload = {
            "event": "doctor_password_reset_requested",
            "message": f"Doctor {full_name} ({email}) has requested a password reset.",
            "data": {
                "user_id": user_id,
                "email": email,
                "full_name": full_name,
            },
        }

        target_sockets: set[str] = set()
        target_sockets.update(self.role_sockets.get("admin", set()))
        target_sockets.update(self.role_sockets.get("super_admin", set()))

        logger.info(
            "Broadcasting doctor_password_reset_requested event to admins",
            user_id=user_id,
            recipient_sockets_count=len(target_sockets),
        )

        await self.broadcast_event(payload, target_sockets)


# Global Singleton Manager
manager = ConnectionManager()


