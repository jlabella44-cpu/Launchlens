"""Tests for expanded Stripe webhook handlers — credit bundle, renewal, cancellation."""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from launchlens.models.tenant import Tenant


def _make_stripe_event(event_type: str, data_object: dict, event_id: str = "evt_test_123"):
    """Build a mock Stripe event."""
    event = MagicMock()
    event.type = event_type
    event.id = event_id
    event.__getitem__ = lambda self, key: {"data": {"object": data_object}}[key]
    return event


async def _create_tenant(db: AsyncSession, **overrides) -> Tenant:
    defaults = dict(
        id=uuid.uuid4(),
        name="Webhook Test Co",
        plan="pro",
        stripe_customer_id=f"cus_{uuid.uuid4().hex[:8]}",
        stripe_subscription_id=f"sub_{uuid.uuid4().hex[:8]}",
        credit_balance=20,
        included_credits=50,
        rollover_cap=25,
    )
    defaults.update(overrides)
    tenant = Tenant(**defaults)
    db.add(tenant)
    await db.commit()
    return tenant


async def _get_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
    db.expire_all()
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    return result.scalar_one()


async def _fire_webhook(async_client: AsyncClient, event: MagicMock) -> int:
    with patch("launchlens.api.billing.BillingService") as MockSvc:
        mock_svc = MockSvc.return_value
        mock_svc.construct_webhook_event.return_value = event
        mock_svc.resolve_plan.return_value = "enterprise"
        resp = await async_client.post(
            "/billing/webhook",
            content=b"raw-payload",
            headers={"stripe-signature": "sig_test"},
        )
    return resp.status_code


@pytest.mark.asyncio
async def test_webhook_credit_bundle_checkout(async_client: AsyncClient, db_session):
    tenant = await _create_tenant(db_session)
    event = _make_stripe_event("checkout.session.completed", {
        "metadata": {
            "tenant_id": str(tenant.id),
            "type": "credit_bundle",
            "bundle_size": "100",
        },
        "id": "cs_bundle_test",
    }, event_id="evt_bundle_1")

    status = await _fire_webhook(async_client, event)
    assert status == 200

    t = await _get_tenant(db_session, tenant.id)
    assert t.credit_balance == 120  # 20 + 100


@pytest.mark.asyncio
async def test_webhook_credit_bundle_idempotent(async_client: AsyncClient, db_session):
    tenant = await _create_tenant(db_session)
    event = _make_stripe_event("checkout.session.completed", {
        "metadata": {
            "tenant_id": str(tenant.id),
            "type": "credit_bundle",
            "bundle_size": "100",
        },
    }, event_id="evt_idem_bundle")

    await _fire_webhook(async_client, event)
    await _fire_webhook(async_client, event)

    t = await _get_tenant(db_session, tenant.id)
    assert t.credit_balance == 120  # only granted once


@pytest.mark.asyncio
async def test_webhook_subscription_deleted_preserves_credits(async_client: AsyncClient, db_session):
    tenant = await _create_tenant(db_session)
    event = _make_stripe_event("customer.subscription.deleted", {
        "customer": tenant.stripe_customer_id,
    }, event_id="evt_cancel_1")

    status = await _fire_webhook(async_client, event)
    assert status == 200

    t = await _get_tenant(db_session, tenant.id)
    assert t.plan == "lite"
    assert t.included_credits == 0
    assert t.credit_balance == 20  # preserved


@pytest.mark.asyncio
async def test_webhook_subscription_updated_changes_tier(async_client: AsyncClient, db_session):
    tenant = await _create_tenant(db_session)
    event = _make_stripe_event("customer.subscription.updated", {
        "customer": tenant.stripe_customer_id,
        "items": {"data": [{"price": {"id": "price_enterprise"}}]},
    }, event_id="evt_upgrade_1")

    status = await _fire_webhook(async_client, event)
    assert status == 200

    t = await _get_tenant(db_session, tenant.id)
    assert t.plan == "enterprise"
    assert t.included_credits == 200
    assert t.rollover_cap == 100


@pytest.mark.asyncio
async def test_webhook_invoice_paid_grants_renewal_credits(async_client: AsyncClient, db_session):
    tenant = await _create_tenant(db_session)
    assert tenant.credit_balance == 20

    event = _make_stripe_event("invoice.paid", {
        "customer": tenant.stripe_customer_id,
        "amount_paid": 9900,
        "id": "inv_renew_1",
    }, event_id="evt_inv_paid_1")

    status = await _fire_webhook(async_client, event)
    assert status == 200

    t = await _get_tenant(db_session, tenant.id)
    # 20 balance, rollover_cap=25, so all 20 roll over, then +50 included
    assert t.credit_balance == 70  # 20 + 50
