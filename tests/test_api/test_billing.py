# tests/test_api/test_billing.py
import pytest
from launchlens.models.tenant import Tenant


def test_tenant_has_stripe_fields():
    """Tenant model must have stripe_customer_id and stripe_subscription_id."""
    import inspect
    annotations = {}
    for cls in reversed(Tenant.__mro__):
        if hasattr(cls, '__annotations__'):
            annotations.update(cls.__annotations__)
    assert "stripe_customer_id" in annotations
    assert "stripe_subscription_id" in annotations
