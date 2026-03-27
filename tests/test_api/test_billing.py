# tests/test_api/test_billing.py
import uuid
import pytest
from unittest.mock import patch, MagicMock
from launchlens.models.tenant import Tenant
from launchlens.services.billing import BillingService


def test_tenant_has_stripe_fields():
    """Tenant model must have stripe_customer_id and stripe_subscription_id."""
    import inspect
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


@patch("launchlens.services.billing.stripe")
def test_create_customer(mock_stripe):
    mock_stripe.Customer.create.return_value = MagicMock(id="cus_test123")
    svc = BillingService()
    cid = svc.create_customer(email="a@b.com", name="Test", tenant_id=str(uuid.uuid4()))
    assert cid == "cus_test123"
    mock_stripe.Customer.create.assert_called_once()


@patch("launchlens.services.billing.stripe")
def test_create_checkout_session(mock_stripe):
    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/pay/cs_test")
    svc = BillingService()
    url = svc.create_checkout_session(
        customer_id="cus_test123",
        price_id="price_pro",
        success_url="https://app.launchlens.com/billing?success=true",
        cancel_url="https://app.launchlens.com/billing?canceled=true",
    )
    assert url == "https://checkout.stripe.com/pay/cs_test"


@patch("launchlens.services.billing.stripe")
def test_create_portal_session(mock_stripe):
    mock_stripe.billing_portal.Session.create.return_value = MagicMock(url="https://billing.stripe.com/session/xyz")
    svc = BillingService()
    url = svc.create_portal_session(
        customer_id="cus_test123",
        return_url="https://app.launchlens.com/billing",
    )
    assert url == "https://billing.stripe.com/session/xyz"


def test_resolve_plan_from_price():
    svc = BillingService()
    # When price_id is not in the map, default to "starter"
    assert svc.resolve_plan("nonexistent_price") == "starter"
