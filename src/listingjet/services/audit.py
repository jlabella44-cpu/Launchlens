"""Audit logging service for admin operations."""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.audit_log import AuditLog


async def audit_log(
    session: AsyncSession,
    user_id: uuid.UUID,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    tenant_id: uuid.UUID | None = None,
    details: dict | None = None,
) -> None:
    """Record an admin action in the audit log."""
    entry = AuditLog(
        user_id=user_id,
        tenant_id=tenant_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
    )
    session.add(entry)
