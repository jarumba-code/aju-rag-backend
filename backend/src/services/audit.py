"""
Audit logging service for the AJU Knowledge Management Platform.

Provides structured audit trail recording for:
- Admin authentication events
- Document management actions
- Settings changes
- Password changes

No passwords, JWTs, API keys, or other secrets are ever stored in audit logs.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AuditLog

logger = logging.getLogger(__name__)


async def record_audit(
    db: AsyncSession,
    action: str,
    status: str = "success",
    user_role: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    """
    Record an audit log entry.

    This is a fire-and-forget style helper — the caller is responsible for
    committing the transaction. If details is provided, it is JSON-serialized
    and stored as a string.
    """
    try:
        details_str = json.dumps(details) if details else None
        log_entry = AuditLog(
            action=action,
            status=status,
            user_role=user_role,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details_str,
            ip_address=ip_address,
            timestamp=datetime.utcnow(),
        )
        db.add(log_entry)
        # We intentionally do NOT commit here — caller controls transaction.
    except Exception as exc:
        logger.warning("Failed to write audit log: %s", exc)


async def get_audit_logs(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    action: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """Query audit logs with optional filters."""
    stmt = select(AuditLog)

    if action:
        stmt = stmt.where(AuditLog.action == action)
    if status:
        stmt = stmt.where(AuditLog.status == status)
    if start_date:
        stmt = stmt.where(AuditLog.timestamp >= start_date)
    if end_date:
        stmt = stmt.where(AuditLog.timestamp <= end_date)

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(total_stmt)
    total = total_result.scalar_one()

    result = await db.execute(
        stmt.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
    )
    logs = result.scalars().all()

    return {
        "total": total,
        "logs": [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "user_role": log.user_role,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "status": log.status,
                "ip_address": log.ip_address,
            }
            for log in logs
        ],
    }
