"""Tests for CreditService."""
import uuid

import pytest
from sqlalchemy import select

from launchlens.models.credit_transaction import CreditTransaction
from launchlens.models.tenant import Tenant
from launchlens.services.credits import CreditService


async def _create_tenant(db_session, plan="pro", credit_balance=0, included_credits=50, rollover_cap=25) -> Tenant:
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Co",
        plan=plan,
        credit_balance=credit_balance,
        included_credits=included_credits,
        rollover_cap=rollover_cap,
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest.mark.asyncio
async def test_add_credits(db_session):
    tenant = await _create_tenant(db_session, credit_balance=10)
    svc = CreditService()

    txn = await svc.add_credits(
        db_session, tenant.id, 50,
        transaction_type="purchase",
        reference_type="stripe_event",
        reference_id="evt_123",
        description="50 credit bundle",
    )

    assert txn is not None
    assert txn.amount == 50
    assert txn.balance_after == 60
    assert tenant.credit_balance == 60


@pytest.mark.asyncio
async def test_add_credits_idempotent(db_session):
    tenant = await _create_tenant(db_session, credit_balance=10)
    svc = CreditService()

    # First call succeeds
    txn1 = await svc.add_credits(
        db_session, tenant.id, 50,
        reference_id="evt_dup",
    )
    assert txn1 is not None
    assert tenant.credit_balance == 60

    # Second call with same reference_id is a no-op
    txn2 = await svc.add_credits(
        db_session, tenant.id, 50,
        reference_id="evt_dup",
    )
    assert txn2 is None
    assert tenant.credit_balance == 60  # unchanged


@pytest.mark.asyncio
async def test_deduct_credits(db_session):
    tenant = await _create_tenant(db_session, credit_balance=100)
    svc = CreditService()

    txn = await svc.deduct_credits(
        db_session, tenant.id, 30,
        reference_id="listing_abc",
        description="Listing processing",
    )

    assert txn is not None
    assert txn.amount == -30
    assert txn.balance_after == 70
    assert tenant.credit_balance == 70


@pytest.mark.asyncio
async def test_deduct_insufficient_balance(db_session):
    tenant = await _create_tenant(db_session, credit_balance=5)
    svc = CreditService()

    txn = await svc.deduct_credits(db_session, tenant.id, 10)
    assert txn is None
    assert tenant.credit_balance == 5  # unchanged


@pytest.mark.asyncio
async def test_process_period_renewal(db_session):
    tenant = await _create_tenant(db_session, credit_balance=30, included_credits=50, rollover_cap=25)
    svc = CreditService()

    result = await svc.process_period_renewal(
        db_session, tenant.id, 50,
        reference_id="evt_renewal_1",
    )

    assert result["old_balance"] == 30
    assert result["rolled_over"] == 25  # capped at rollover_cap
    assert result["expired"] == 5  # 30 - 25 = 5 expired
    assert result["granted"] == 50
    assert result["new_balance"] == 75  # 25 (rolled) + 50 (granted)
    assert tenant.credit_balance == 75


@pytest.mark.asyncio
async def test_process_period_renewal_idempotent(db_session):
    tenant = await _create_tenant(db_session, credit_balance=10, included_credits=50, rollover_cap=25)
    svc = CreditService()

    result1 = await svc.process_period_renewal(
        db_session, tenant.id, 50,
        reference_id="evt_renew_dup",
    )
    assert result1["new_balance"] == 60

    # Second call is idempotent
    result2 = await svc.process_period_renewal(
        db_session, tenant.id, 50,
        reference_id="evt_renew_dup",
    )
    assert result2.get("skipped") is True
    assert tenant.credit_balance == 60  # unchanged


@pytest.mark.asyncio
async def test_process_period_renewal_no_expiry_when_under_cap(db_session):
    tenant = await _create_tenant(db_session, credit_balance=10, included_credits=50, rollover_cap=25)
    svc = CreditService()

    result = await svc.process_period_renewal(
        db_session, tenant.id, 50,
        reference_id="evt_renew_under",
    )

    assert result["expired"] == 0  # 10 < 25 cap, nothing expired
    assert result["rolled_over"] == 10
    assert result["new_balance"] == 60  # 10 + 50


@pytest.mark.asyncio
async def test_get_balance(db_session):
    tenant = await _create_tenant(db_session, credit_balance=42)
    svc = CreditService()

    balance = await svc.get_balance(db_session, tenant.id)
    assert balance == 42


@pytest.mark.asyncio
async def test_get_balance_nonexistent_tenant(db_session):
    svc = CreditService()
    balance = await svc.get_balance(db_session, uuid.uuid4())
    assert balance == 0
