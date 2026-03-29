# tests/test_api/test_billing.py
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from listingjet.models.tenant import Tenant
from listingjet.services.billing import BillingService


def test_tenant_has_stripe_fields():
    """Tenant model must have stripe_customer_id and stripe_subscription_id."""
    annotations = {}
    for cls in reversed(Tenant.__mro__):
        if hasattr(cls, '__annotations__'):
            annotations.update(cls.__annotations__)
    assert "stripe_customer_id" in annotations
    assert "stripe_subscription_id" in annotations


def _make_tenant(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "name": "Test Co",
        "plan": "starter",
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
    }
    defaults.update(overrides)
    t = Tenant.__new__(Tenant)
    for k, v in defaults.items():
        setattr(t, k, v)
    return t


@patch("listingjet.services.billing.stripe")
def test_create_customer(mock_stripe):
    mock_stripe.Customer.create.return_value = MagicMock(id="cus_test123")
    svc = BillingService()
    cid = svc.create_customer(email="a@b.com", name="Test", tenant_id=str(uuid.uuid4()))
    assert cid == "cus_test123"
    mock_stripe.Customer.create.assert_called_once()


@patch("listingjet.services.billing.stripe")
def test_create_checkout_session(mock_stripe):
    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/pay/cs_test")
    svc = BillingService()
    url = svc.create_checkout_session(
        customer_id="cus_test123",
        price_id="price_pro",
        success_url="https://app.listingjet.com/billing?success=true",
        cancel_url="https://app.listingjet.com/billing?canceled=true",
    )
    assert url == "https://checkout.stripe.com/pay/cs_test"


@patch("listingjet.services.billing.stripe")
def test_create_portal_session(mock_stripe):
    mock_stripe.billing_portal.Session.create.return_value = MagicMock(url="https://billing.stripe.com/session/xyz")
    svc = BillingService()
    url = svc.create_portal_session(
        customer_id="cus_test123",
        return_url="https://app.listingjet.com/billing",
    )
    assert url == "https://billing.stripe.com/session/xyz"


def test_resolve_plan_from_price():
    svc = BillingService()
    # When price_id is not in the map, default to "starter"
    assert svc.resolve_plan("nonexistent_price") == "starter"


@pytest.mark.asyncio
@patch("listingjet.api.billing.BillingService")
async def test_checkout_returns_url(MockBilling, async_client: AsyncClient):
    email = f"test-{uuid.uuid4()}@example.com"
    reg = await async_client.post("/auth/register", json={
        "email": email, "password": "StrongPass1!", "name": "Test", "company_name": "TestCo"
    })
    token = reg.json()["access_token"]

    mock_svc = MockBilling.return_value
    mock_svc.create_customer.return_value = "cus_new"
    mock_svc.create_checkout_session.return_value = "https://checkout.stripe.com/pay/cs_test"

    resp = await async_client.post(
        "/billing/checkout",
        json={"price_id": "price_pro", "success_url": "https://app.test/ok", "cancel_url": "https://app.test/no"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["checkout_url"] == "https://checkout.stripe.com/pay/cs_test"


@pytest.mark.asyncio
async def test_billing_status_returns_plan(async_client: AsyncClient):
    email = f"test-{uuid.uuid4()}@example.com"
    reg = await async_client.post("/auth/register", json={
        "email": email, "password": "StrongPass1!", "name": "Test", "company_name": "PlanCo"
    })
    token = reg.json()["access_token"]

    resp = await async_client.get(
        "/billing/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "starter"
    assert body["stripe_customer_id"] is None


@pytest.mark.asyncio
async def test_checkout_requires_auth(async_client: AsyncClient):
    resp = await async_client.post("/billing/checkout", json={
        "price_id": "price_pro",
        "success_url": "https://app.test/ok",
        "cancel_url": "https://app.test/no",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
@patch("listingjet.api.billing.BillingService")
async def test_webhook_checkout_completed_updates_plan(MockBilling, async_client: AsyncClient, db_session):
    from listingjet.models.tenant import Tenant

    tenant = Tenant(
        id=uuid.uuid4(), name="WebhookCo", plan="starter",
        stripe_customer_id="cus_wh1", stripe_subscription_id=None,
    )
    db_session.add(tenant)
    await db_session.commit()

    mock_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_wh1",
                "subscription": "sub_new123",
                "metadata": {"tenant_id": str(tenant.id)},
            }
        },
    }
    mock_svc = MockBilling.return_value
    mock_svc.construct_webhook_event.return_value = MagicMock(**mock_event)
    mock_svc.construct_webhook_event.return_value.type = "checkout.session.completed"
    mock_svc.construct_webhook_event.return_value.__getitem__ = lambda self, key: mock_event[key]

    resp = await async_client.post(
        "/billing/webhook",
        content=json.dumps(mock_event),
        headers={"stripe-signature": "test_sig", "content-type": "application/json"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
@patch("listingjet.api.billing.BillingService")
async def test_webhook_subscription_deleted_downgrades(MockBilling, async_client: AsyncClient, db_session):
    from listingjet.models.tenant import Tenant

    tenant = Tenant(
        id=uuid.uuid4(), name="DowngradeCo", plan="pro",
        stripe_customer_id="cus_wh2", stripe_subscription_id="sub_old",
    )
    db_session.add(tenant)
    await db_session.commit()

    mock_event = {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "customer": "cus_wh2",
                "metadata": {"tenant_id": str(tenant.id)},
            }
        },
    }
    mock_svc = MockBilling.return_value
    mock_svc.construct_webhook_event.return_value = MagicMock(**mock_event)
    mock_svc.construct_webhook_event.return_value.type = "customer.subscription.deleted"
    mock_svc.construct_webhook_event.return_value.__getitem__ = lambda self, key: mock_event[key]

    resp = await async_client.post(
        "/billing/webhook",
        content=json.dumps(mock_event),
        headers={"stripe-signature": "test_sig", "content-type": "application/json"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_webhook_missing_signature_returns_400(async_client: AsyncClient):
    resp = await async_client.post(
        "/billing/webhook",
        content=b'{"type": "test"}',
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 400
