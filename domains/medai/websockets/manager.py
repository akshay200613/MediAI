"""
WebSocket Connection Manager for MediAI.
Manages tab-isolated WebSocket connections grouped by user_id, role, patient_id, and doctor_id.
Supports multi-worker horizontal scaling via Redis Pub/Sub broadcast distribution.
"""

import asyncio
from collections import defaultdict
import json
from typing import Any
from fastapi import WebSocket

from core.config.logging import get_logger
from core.database.redis_client import get_redis
from core.database.redis_keys import WS_BROADCAST_CHANNEL
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

        self._pubsub_task: asyncio.Task | None = None
        self._is_listening = False

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
        """Broadcast a JSON payload to a specific set of active socket_ids on this worker."""
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

    async def _deliver_local_event(
        self,
        payload: dict[str, Any],
        roles: list[str] | None = None,
        patient_ids: list[str] | None = None,
        doctor_ids: list[str] | None = None,
        user_ids: list[str] | None = None,
    ) -> None:
        """Deliver an event to matching local sockets on this process."""
        target_sockets: set[str] = set()

        if roles:
            for r in roles:
                target_sockets.update(self.role_sockets.get(r, set()))

        if patient_ids:
            for pid in patient_ids:
                pid_str = str(pid)
                if pid_str in self.patient_sockets:
                    target_sockets.update(self.patient_sockets[pid_str])
                if pid_str in self.user_sockets:
                    target_sockets.update(self.user_sockets[pid_str])

        if doctor_ids:
            for did in doctor_ids:
                did_str = str(did)
                if did_str in self.doctor_sockets:
                    target_sockets.update(self.doctor_sockets[did_str])
                if did_str in self.user_sockets:
                    target_sockets.update(self.user_sockets[did_str])

        if user_ids:
            for uid in user_ids:
                uid_str = str(uid)
                if uid_str in self.user_sockets:
                    target_sockets.update(self.user_sockets[uid_str])

        if target_sockets:
            await self.broadcast_event(payload, target_sockets)

    async def _publish_distributed_event(
        self,
        payload: dict[str, Any],
        roles: list[str] | None = None,
        patient_ids: list[str] | None = None,
        doctor_ids: list[str] | None = None,
        user_ids: list[str] | None = None,
    ) -> None:
        """
        Publish event to Redis Pub/Sub channel so all worker processes receive and dispatch it.
        Falls back to local delivery immediately if Redis is unreachable.
        """
        event_envelope = {
            "payload": payload,
            "roles": roles or [],
            "patient_ids": patient_ids or [],
            "doctor_ids": doctor_ids or [],
            "user_ids": user_ids or [],
        }

        published_to_redis = False
        try:
            redis = get_redis()
            await redis.publish(WS_BROADCAST_CHANNEL, json.dumps(event_envelope))
            published_to_redis = True
        except Exception as e:
            logger.debug(f"Redis unavailable for WebSocket pubsub broadcast: {e}")

        # If Redis is unavailable or we're not actively listening on pubsub, deliver locally
        if not published_to_redis or not self._is_listening:
            await self._deliver_local_event(
                payload=payload,
                roles=roles,
                patient_ids=patient_ids,
                doctor_ids=doctor_ids,
                user_ids=user_ids,
            )

    async def notify_appointment_event(
        self,
        event_type: str,  # "appointment_created" | "appointment_updated" | "appointment_cancelled"
        appointment_data: dict[str, Any],
        patient_id: str | None = None,
        doctor_id: str | None = None,
    ) -> None:
        """
        Notify all connected portals (patients, doctors, admins) across all workers.
        """
        payload = {
            "event": event_type,
            "data": appointment_data,
        }
        roles = ["admin", "super_admin", "doctor"]
        patient_ids = [str(patient_id)] if patient_id else []
        doctor_ids = [str(doctor_id)] if doctor_id else []

        await self._publish_distributed_event(
            payload=payload,
            roles=roles,
            patient_ids=patient_ids,
            doctor_ids=doctor_ids,
        )

    async def notify_doctor_updated(
        self,
        doctor_id: str,
        doctor_data: dict[str, Any],
        changes_summary: str | None = None,
    ) -> None:
        """
        Notify target doctor and admins across all workers when admin edits doctor profile.
        """
        payload = {
            "event": "doctor_updated",
            "message": changes_summary or "Admin has updated your profile details.",
            "data": doctor_data,
        }
        roles = ["admin", "super_admin", "doctor"]
        doctor_ids = [str(doctor_id)] if doctor_id else []

        await self._publish_distributed_event(
            payload=payload,
            roles=roles,
            doctor_ids=doctor_ids,
        )

    async def notify_admin_password_reset_request(
        self,
        user_id: str,
        email: str,
        full_name: str,
    ) -> None:
        """
        Notify all admins across all workers when a user/doctor requests a password reset.
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
        roles = ["admin", "super_admin"]

        await self._publish_distributed_event(
            payload=payload,
            roles=roles,
        )

    def start_pubsub_listener(self) -> None:
        """Start the background Redis Pub/Sub listener task for this worker."""
        if self._is_listening:
            return
        self._is_listening = True
        self._pubsub_task = asyncio.create_task(self._pubsub_loop())
        logger.info("WebSocket Redis Pub/Sub listener started")

    async def stop_pubsub_listener(self) -> None:
        """Stop the background Redis Pub/Sub listener gracefully."""
        self._is_listening = False
        if self._pubsub_task and not self._pubsub_task.done():
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass
        logger.info("WebSocket Redis Pub/Sub listener stopped")

    async def _pubsub_loop(self) -> None:
        """Background loop reading broadcast events from Redis Pub/Sub."""
        while self._is_listening:
            pubsub = None
            try:
                redis = get_redis()
                pubsub = redis.pubsub()
                await pubsub.subscribe(WS_BROADCAST_CHANNEL)
                logger.info("Subscribed to WebSocket Redis Pub/Sub channel", channel=WS_BROADCAST_CHANNEL)

                while self._is_listening:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message.get("type") == "message":
                        try:
                            data_str = message.get("data")
                            if data_str:
                                envelope = json.loads(data_str)
                                await self._deliver_local_event(
                                    payload=envelope.get("payload", {}),
                                    roles=envelope.get("roles"),
                                    patient_ids=envelope.get("patient_ids"),
                                    doctor_ids=envelope.get("doctor_ids"),
                                    user_ids=envelope.get("user_ids"),
                                )
                        except Exception as parse_err:
                            logger.warning(f"Error parsing Pub/Sub WebSocket message: {parse_err}")

                    await asyncio.sleep(0.01)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug(f"Redis Pub/Sub listener disconnected, retrying in 3s: {exc}")
                await asyncio.sleep(3.0)
            finally:
                if pubsub:
                    try:
                        await pubsub.unsubscribe(WS_BROADCAST_CHANNEL)
                        await pubsub.aclose()
                    except Exception:
                        pass


# Global Singleton Manager
manager = ConnectionManager()
