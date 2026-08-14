"""
RBAC Permission System.
Fine-grained permissions on top of roles.
"""

from enum import StrEnum
from functools import lru_cache
from typing import Callable

from fastapi import Depends, HTTPException, status

from core.auth.dependencies import CurrentUser, get_current_user


class Permission(StrEnum):
    # Platform
    MANAGE_USERS = "platform:manage_users"
    VIEW_AUDIT_LOGS = "platform:view_audit_logs"

    # MedAI – Patients
    CREATE_PATIENT = "medai:create_patient"
    VIEW_PATIENT = "medai:view_patient"
    UPDATE_PATIENT = "medai:update_patient"
    DELETE_PATIENT = "medai:delete_patient"

    # MedAI – Appointments
    CREATE_APPOINTMENT = "medai:create_appointment"
    VIEW_APPOINTMENT = "medai:view_appointment"
    UPDATE_APPOINTMENT = "medai:update_appointment"

    # MedAI – Prescriptions
    CREATE_PRESCRIPTION = "medai:create_prescription"
    VIEW_PRESCRIPTION = "medai:view_prescription"

    # AI
    USE_AI_CHAT = "ai:use_chat"
    MANAGE_KNOWLEDGE_BASE = "ai:manage_knowledge_base"


# Role → Permissions mapping
ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "super_admin": set(Permission),  # All permissions
    "admin": {
        Permission.MANAGE_USERS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.CREATE_PATIENT,
        Permission.VIEW_PATIENT,
        Permission.UPDATE_PATIENT,
        Permission.DELETE_PATIENT,
        Permission.CREATE_APPOINTMENT,
        Permission.VIEW_APPOINTMENT,
        Permission.UPDATE_APPOINTMENT,
        Permission.CREATE_PRESCRIPTION,
        Permission.VIEW_PRESCRIPTION,
        Permission.USE_AI_CHAT,
        Permission.MANAGE_KNOWLEDGE_BASE,
    },
    "doctor": {
        Permission.VIEW_PATIENT,
        Permission.UPDATE_PATIENT,
        Permission.CREATE_APPOINTMENT,
        Permission.VIEW_APPOINTMENT,
        Permission.UPDATE_APPOINTMENT,
        Permission.CREATE_PRESCRIPTION,
        Permission.VIEW_PRESCRIPTION,
        Permission.USE_AI_CHAT,
    },
    "nurse": {
        Permission.VIEW_PATIENT,
        Permission.CREATE_APPOINTMENT,
        Permission.VIEW_APPOINTMENT,
        Permission.VIEW_PRESCRIPTION,
        Permission.USE_AI_CHAT,
    },
    "receptionist": {
        Permission.VIEW_PATIENT,
        Permission.CREATE_PATIENT,
        Permission.CREATE_APPOINTMENT,
        Permission.VIEW_APPOINTMENT,
        Permission.UPDATE_APPOINTMENT,
    },
    "patient": {
        Permission.USE_AI_CHAT,
        Permission.VIEW_APPOINTMENT,
        Permission.CREATE_APPOINTMENT,
        Permission.UPDATE_APPOINTMENT,
        Permission.VIEW_PATIENT,
        Permission.UPDATE_PATIENT,
    },
    "user": {
        Permission.USE_AI_CHAT,
        Permission.VIEW_APPOINTMENT,
        Permission.CREATE_APPOINTMENT,
        Permission.UPDATE_APPOINTMENT,
        Permission.VIEW_PATIENT,
        Permission.UPDATE_PATIENT,
    },
}


def has_permission(role: str, permission: Permission) -> bool:
    """Check if a role has a given permission."""
    return permission in ROLE_PERMISSIONS.get(role, set())


def require_permission(permission: Permission) -> Callable:
    """
    Dependency factory: raises 403 if the user lacks the required permission.

    Usage:
        @router.post("/", dependencies=[Depends(require_permission(Permission.CREATE_PATIENT))])
    """
    async def _guard(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return current_user
    return _guard
