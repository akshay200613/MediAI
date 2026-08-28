"""
Audit Logging Service – helper functions for creating persistent audit log entries.
"""

import json
from typing import Any
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.audit_log import AuditLog
from core.config.logging import get_logger

logger = get_logger("audit")


async def log_audit_event(
    session: AsyncSession,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict[str, Any] | str | None = None,
    ip_address: str | None = None,
    user_name: str | None = None,
    user_role: str | None = None,
    request: Request | None = None,
) -> AuditLog:
    """
    Records an audit log entry in the database and structured python log.
    """
    if request and not ip_address:
        ip_address = request.client.host if request.client else None

    details_str = None
    if details is not None:
        if isinstance(details, (dict, list)):
            try:
                details_str = json.dumps(details, default=str)
            except Exception:
                details_str = str(details)
        else:
            details_str = str(details)

    audit_entry = AuditLog(
        user_id=str(user_id) if user_id else "system",
        user_name=user_name,
        user_role=user_role,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        details=details_str,
        ip_address=ip_address or "127.0.0.1",
    )

    try:
        session.add(audit_entry)
        await session.flush()
        logger.info(
            "AUDIT_EVENT",
            action=action,
            user_id=str(user_id),
            user_name=user_name,
            resource_type=resource_type,
            resource_id=resource_id,
            ip=ip_address,
        )
    except Exception as exc:
        logger.error(f"Failed to write audit log entry: {exc}")

    return audit_entry
