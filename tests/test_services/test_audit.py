"""Tests for the audit logging service."""
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.audit_log import AuditLog
from listingjet.services.audit import audit_log


@pytest.mark.asyncio
async def test_audit_log_creates_entry(db_session: AsyncSession):
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    await audit_log(
        session=db_session,
        user_id=user_id,
        action="tenant.update",
        resource_type="tenant",
        resource_id=str(tenant_id),
        tenant_id=tenant_id,
        details={"plan": "pro"},
    )
    await db_session.flush()

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.user_id == user_id)
    )
    entries = result.scalars().all()
    assert len(entries) == 1
    assert entries[0].action == "tenant.update"
    assert entries[0].user_id == user_id
    assert entries[0].details == {"plan": "pro"}


@pytest.mark.asyncio
async def test_audit_log_defaults_details_to_empty_dict(db_session: AsyncSession):
    uid = uuid.uuid4()
    await audit_log(
        session=db_session,
        user_id=uid,
        action="listing.delete",
        resource_type="listing",
    )
    await db_session.flush()

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.user_id == uid)
    )
    entry = result.scalars().first()
    assert entry.details == {}
