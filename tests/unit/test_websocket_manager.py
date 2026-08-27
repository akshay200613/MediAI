"""
Unit tests for the WebSocket ConnectionManager.

Pure unit tests – no real FastAPI app, no real WebSocket connections.
Uses mock WebSocket objects to verify connection tracking and broadcasting.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import asyncio

from domains.medai.websockets.manager import ConnectionManager


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_ws() -> MagicMock:
    """Create a mock WebSocket that records send_json calls."""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


async def _connect(
    mgr: ConnectionManager,
    ws: MagicMock,
    socket_id: str,
    user_id: str = "user-1",
    role: str = "patient",
    patient_id: str | None = None,
    doctor_id: str | None = None,
) -> None:
    await mgr.connect(
        websocket=ws,
        socket_id=socket_id,
        user_id=user_id,
        role=role,
        patient_id=patient_id,
        doctor_id=doctor_id,
    )


# ─── connect / disconnect ─────────────────────────────────────────────────────

class TestConnectionRegistration:
    async def test_connect_registers_socket(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        await _connect(mgr, ws, "s1", user_id="u1", role="patient")

        assert "s1" in mgr.active_connections
        assert mgr.active_connections["s1"] is ws

    async def test_connect_calls_websocket_accept(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        await _connect(mgr, ws, "s1")

        ws.accept.assert_called_once()

    async def test_connect_adds_to_user_sockets(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        await _connect(mgr, ws, "s1", user_id="u1")

        assert "s1" in mgr.user_sockets["u1"]

    async def test_connect_adds_to_role_sockets(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        await _connect(mgr, ws, "s1", role="doctor")

        assert "s1" in mgr.role_sockets["doctor"]

    async def test_connect_with_patient_id_registers_in_patient_sockets(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        await _connect(mgr, ws, "s1", patient_id="pat-123")

        assert "s1" in mgr.patient_sockets["pat-123"]

    async def test_connect_with_doctor_id_registers_in_doctor_sockets(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        await _connect(mgr, ws, "s1", doctor_id="doc-456")

        assert "s1" in mgr.doctor_sockets["doc-456"]

    async def test_connect_without_patient_or_doctor_ids_no_extra_entries(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        await _connect(mgr, ws, "s1")

        assert len(mgr.patient_sockets) == 0
        assert len(mgr.doctor_sockets) == 0

    async def test_disconnect_removes_from_active_connections(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        await _connect(mgr, ws, "s1", user_id="u1", role="admin")
        mgr.disconnect("s1")

        assert "s1" not in mgr.active_connections

    async def test_disconnect_removes_from_user_sockets(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        await _connect(mgr, ws, "s1", user_id="u1")
        mgr.disconnect("s1")

        assert "s1" not in mgr.user_sockets["u1"]

    async def test_disconnect_removes_from_role_sockets(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        await _connect(mgr, ws, "s1", role="nurse")
        mgr.disconnect("s1")

        assert "s1" not in mgr.role_sockets["nurse"]

    async def test_disconnect_removes_from_patient_sockets(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        await _connect(mgr, ws, "s1", patient_id="pat-999")
        mgr.disconnect("s1")

        assert "s1" not in mgr.patient_sockets.get("pat-999", set())

    async def test_disconnect_removes_from_doctor_sockets(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        await _connect(mgr, ws, "s1", doctor_id="doc-888")
        mgr.disconnect("s1")

        assert "s1" not in mgr.doctor_sockets.get("doc-888", set())

    async def test_disconnect_unknown_socket_is_idempotent(self):
        """Disconnecting a non-existent socket must not raise."""
        mgr = ConnectionManager()
        mgr.disconnect("does-not-exist")  # should not raise

    async def test_two_users_have_isolated_socket_sets(self):
        mgr = ConnectionManager()
        ws1, ws2 = _make_ws(), _make_ws()
        await _connect(mgr, ws1, "s1", user_id="u1")
        await _connect(mgr, ws2, "s2", user_id="u2")

        assert mgr.user_sockets["u1"] == {"s1"}
        assert mgr.user_sockets["u2"] == {"s2"}


# ─── broadcast_event ─────────────────────────────────────────────────────────

class TestBroadcast:
    async def test_broadcast_sends_to_all_target_sockets(self):
        mgr = ConnectionManager()
        ws1, ws2, ws3 = _make_ws(), _make_ws(), _make_ws()
        await _connect(mgr, ws1, "s1")
        await _connect(mgr, ws2, "s2")
        await _connect(mgr, ws3, "s3")

        payload = {"event": "test", "data": {}}
        await mgr.broadcast_event(payload, {"s1", "s2"})

        ws1.send_json.assert_called_once_with(payload)
        ws2.send_json.assert_called_once_with(payload)
        ws3.send_json.assert_not_called()

    async def test_broadcast_to_empty_set_does_nothing(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        await _connect(mgr, ws, "s1")
        await mgr.broadcast_event({"event": "noop"}, set())
        ws.send_json.assert_not_called()

    async def test_broadcast_removes_dead_sockets_on_send_failure(self):
        """Sockets that raise on send_json should be disconnected automatically."""
        mgr = ConnectionManager()
        ws = _make_ws()
        ws.send_json = AsyncMock(side_effect=RuntimeError("connection reset"))
        await _connect(mgr, ws, "s1", user_id="u1")

        await mgr.broadcast_event({"event": "ping"}, {"s1"})

        assert "s1" not in mgr.active_connections

    async def test_broadcast_removes_missing_sockets_from_set(self):
        """Socket IDs that are not in active_connections should be cleaned up."""
        mgr = ConnectionManager()
        # Add socket to user map but not to active_connections
        mgr.user_sockets["u1"].add("ghost-socket")

        # Should not raise even though "ghost-socket" is not in active_connections
        await mgr.broadcast_event({"event": "ghost"}, {"ghost-socket"})


# ─── notify_appointment_event ─────────────────────────────────────────────────

class TestNotifyAppointmentEvent:
    async def test_notifies_admin_sockets(self):
        mgr = ConnectionManager()
        admin_ws = _make_ws()
        await _connect(mgr, admin_ws, "admin-s1", role="admin")

        appt_data = {"id": "appt-1", "status": "scheduled"}
        await mgr.notify_appointment_event("appointment_created", appt_data)

        admin_ws.send_json.assert_called_once()
        payload = admin_ws.send_json.call_args[0][0]
        assert payload["event"] == "appointment_created"

    async def test_notifies_super_admin_sockets(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        await _connect(mgr, ws, "sa-s1", role="super_admin")

        await mgr.notify_appointment_event("appointment_updated", {"id": "a1"})

        ws.send_json.assert_called_once()

    async def test_notifies_target_patient_sockets(self):
        mgr = ConnectionManager()
        patient_ws = _make_ws()
        other_ws = _make_ws()
        await _connect(mgr, patient_ws, "p-s1", patient_id="pat-111")
        await _connect(mgr, other_ws, "p-s2", patient_id="pat-222")

        await mgr.notify_appointment_event(
            "appointment_created", {"id": "a1"}, patient_id="pat-111"
        )

        patient_ws.send_json.assert_called_once()
        other_ws.send_json.assert_not_called()

    async def test_notifies_target_doctor_sockets(self):
        mgr = ConnectionManager()
        doc_ws = _make_ws()
        other_ws = _make_ws()
        await _connect(mgr, doc_ws, "d-s1", doctor_id="doc-111")
        await _connect(mgr, other_ws, "d-s2", doctor_id="doc-222")

        await mgr.notify_appointment_event(
            "appointment_cancelled", {"id": "a1"}, doctor_id="doc-111"
        )

        doc_ws.send_json.assert_called_once()
        other_ws.send_json.assert_not_called()

    async def test_notifies_both_patient_and_doctor(self):
        mgr = ConnectionManager()
        p_ws = _make_ws()
        d_ws = _make_ws()
        await _connect(mgr, p_ws, "ps1", patient_id="pat-X")
        await _connect(mgr, d_ws, "ds1", doctor_id="doc-Y")

        await mgr.notify_appointment_event(
            "appointment_created",
            {"id": "a1"},
            patient_id="pat-X",
            doctor_id="doc-Y",
        )

        p_ws.send_json.assert_called_once()
        d_ws.send_json.assert_called_once()

    async def test_notify_without_patient_or_doctor_only_admins(self):
        mgr = ConnectionManager()
        admin_ws = _make_ws()
        patient_ws = _make_ws()
        await _connect(mgr, admin_ws, "as1", role="admin")
        await _connect(mgr, patient_ws, "ps1", patient_id="pat-Z")

        await mgr.notify_appointment_event("appointment_updated", {"id": "a1"})

        admin_ws.send_json.assert_called_once()
        patient_ws.send_json.assert_not_called()

    async def test_payload_structure(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        await _connect(mgr, ws, "s1", role="admin")

        data = {"id": "appt-99", "status": "cancelled"}
        await mgr.notify_appointment_event("appointment_cancelled", data)

        call_args = ws.send_json.call_args[0][0]
        assert call_args["event"] == "appointment_cancelled"
        assert call_args["data"] == data

    async def test_multiple_admin_sockets_all_notified(self):
        mgr = ConnectionManager()
        ws1, ws2 = _make_ws(), _make_ws()
        await _connect(mgr, ws1, "a1", role="admin")
        await _connect(mgr, ws2, "a2", role="admin")

        await mgr.notify_appointment_event("appointment_created", {"id": "x"})

        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()
