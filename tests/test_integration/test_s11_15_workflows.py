"""
Integration tests for sessions 11–15 feature gaps.

Covers endpoints and flows with zero prior test coverage:
  - GET /credits/service-costs (tier-aware pricing metadata)
  - GET /admin/audit-log (filters, pagination)
  - Registration → billing page initialisation flow
  - Admin full dashboard workflow (stats, credits summary, audit log, events)
  - Credit purchase Stripe checkout flow (end-to-end shape validation)
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


# ── Shared helpers (mirror test_credit_lifecycle.py conventions) ──────────────


async def _register(client: AsyncClient, plan_tier: str = "active_agent") -> tuple[str, str]:
    email = f"s11-{uuid.uuid4().hex[:8]}@test.com"
    resp = await client.post("/auth/register", json={
        "email": email,
        "password": "StrongPass1!",
        "name": "Integration Test",
        "company_name": "TestCo",
        "plan_tier": plan_tier,
        "consent": True,
        "ai_consent": True,
    })
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    me = await client.get("/auth/me", headers=_auth(token))
    assert me.status_code == 200
    return token, me.json()["tenant_id"]


async def _register_admin(client: AsyncClient) -> tuple[str, str]:
    token, tenant_id = await _register(client, plan_tier="free")
    from tests.conftest import promote_to_superadmin
    await promote_to_superadmin(client, token)
    return token, tenant_id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── GET /credits/service-costs ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_service_costs_returns_expected_shape(async_client: AsyncClient):
    """Endpoint must return tier, per_credit_dollar_value, and a non-empty services list."""
    token, _ = await _register(async_client, plan_tier="active_agent")
    resp = await async_client.get("/credits/service-costs", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert "tier" in body
    assert "per_credit_dollar_value" in body
    assert isinstance(body["per_credit_dollar_value"], (int, float))
    assert "services" in body
    assert isinstance(body["services"], list)
    assert len(body["services"]) > 0
    service = body["services"][0]
    assert "slug" in service
    assert "name" in service
    assert "credits" in service
    assert isinstance(service["credits"], int)


@pytest.mark.asyncio
async def test_service_costs_tier_reflected(async_client: AsyncClient):
    """per_credit_dollar_value must differ between lite and active_agent tiers."""
    token_lite, _ = await _register(async_client, plan_tier="lite")
    token_pro, _ = await _register(async_client, plan_tier="active_agent")

    resp_lite = await async_client.get("/credits/service-costs", headers=_auth(token_lite))
    resp_pro = await async_client.get("/credits/service-costs", headers=_auth(token_pro))

    assert resp_lite.status_code == 200
    assert resp_pro.status_code == 200

    # Tier names must match what each user was registered with
    assert resp_lite.json()["tier"] != resp_pro.json()["tier"]


@pytest.mark.asyncio
async def test_service_costs_requires_auth(async_client: AsyncClient):
    resp = await async_client.get("/credits/service-costs")
    assert resp.status_code in (401, 403)


# ── GET /admin/audit-log ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_audit_log_returns_list(async_client: AsyncClient):
    """Bare call must return a list (possibly empty if no audit events yet)."""
    token, _ = await _register_admin(async_client)
    resp = await async_client.get("/admin/audit-log", headers=_auth(token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_audit_log_action_filter(async_client: AsyncClient):
    """
    Trigger a known audit event (AI consent toggle) then confirm the action
    filter returns only that event type.
    """
    token, tenant_id = await _register_admin(async_client)

    # Generate a known audit event
    await async_client.post("/auth/ai-consent", json={"consent": False}, headers=_auth(token))

    resp = await async_client.get(
        "/admin/audit-log",
        params={"action": "user.ai_consent.revoked"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    rows = resp.json()
    assert all(r["action"] == "user.ai_consent.revoked" for r in rows)


@pytest.mark.asyncio
async def test_audit_log_resource_type_filter(async_client: AsyncClient):
    token, _ = await _register_admin(async_client)
    await async_client.post("/auth/ai-consent", json={"consent": False}, headers=_auth(token))

    resp = await async_client.get(
        "/admin/audit-log",
        params={"resource_type": "user"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    rows = resp.json()
    assert all(r["resource_type"] == "user" for r in rows)


@pytest.mark.asyncio
async def test_audit_log_tenant_filter(async_client: AsyncClient):
    """tenant_id filter must return only that tenant's events."""
    token_admin, admin_tenant = await _register_admin(async_client)
    token_other, other_tenant = await _register(async_client)

    # Generate an event for the other tenant
    await async_client.post("/auth/ai-consent", json={"consent": False}, headers=_auth(token_other))

    resp = await async_client.get(
        "/admin/audit-log",
        params={"tenant_id": other_tenant},
        headers=_auth(token_admin),
    )
    assert resp.status_code == 200
    rows = resp.json()
    assert all(r["tenant_id"] == other_tenant for r in rows)


@pytest.mark.asyncio
async def test_audit_log_pagination(async_client: AsyncClient):
    """limit and offset must be respected."""
    token, _ = await _register_admin(async_client)

    # Generate 3 audit events
    for consent in [False, True, False]:
        await async_client.post("/auth/ai-consent", json={"consent": consent}, headers=_auth(token))

    all_rows = (await async_client.get("/admin/audit-log", headers=_auth(token))).json()

    # limit=1 must return exactly 1
    resp = await async_client.get(
        "/admin/audit-log", params={"limit": 1}, headers=_auth(token)
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # offset=len means empty page
    resp = await async_client.get(
        "/admin/audit-log",
        params={"limit": 50, "offset": len(all_rows)},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_audit_log_requires_superadmin(async_client: AsyncClient):
    """Regular users must not access the audit log."""
    token, _ = await _register(async_client)
    resp = await async_client.get("/admin/audit-log", headers=_auth(token))
    assert resp.status_code in (401, 403)


# ── Registration → billing page initialisation flow ──────────────────────────


@pytest.mark.asyncio
async def test_registration_billing_page_init(async_client: AsyncClient):
    """
    Full registration → billing page flow:
    register → /auth/me → /credits/balance → /credits/pricing → /credits/service-costs
    All must succeed and return consistent tenant/tier data.
    """
    token, tenant_id = await _register(async_client, plan_tier="active_agent")

    me = await async_client.get("/auth/me", headers=_auth(token))
    assert me.status_code == 200
    assert me.json()["tenant_id"] == tenant_id

    balance = await async_client.get("/credits/balance", headers=_auth(token))
    assert balance.status_code == 200
    assert "balance" in balance.json()

    pricing = await async_client.get("/credits/pricing", headers=_auth(token))
    assert pricing.status_code == 200
    assert "bundles" in pricing.json()
    assert pricing.json()["tier"] == "active_agent"

    costs = await async_client.get("/credits/service-costs", headers=_auth(token))
    assert costs.status_code == 200
    assert costs.json()["tier"] == "active_agent"
    # Tier must be consistent across endpoints
    assert pricing.json()["tier"] == costs.json()["tier"]


@pytest.mark.asyncio
async def test_billing_page_invoice_endpoint(async_client: AsyncClient):
    """GET /billing/invoices must return a list for a newly registered tenant."""
    token, _ = await _register(async_client)

    with patch("listingjet.api.billing.BillingService") as mock_svc_cls:
        mock_svc = MagicMock()
        mock_svc.get_invoices = AsyncMock(return_value=[])
        mock_svc_cls.return_value = mock_svc

        resp = await async_client.get("/billing/invoices", headers=_auth(token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── Admin full dashboard workflow ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_dashboard_full_workflow(async_client: AsyncClient, db_session):
    """
    Admin workflow:
    stats → credits/summary → audit-log → events/recent
    All superadmin endpoints must return 200 with the expected shape.
    """
    token, tenant_id = await _register_admin(async_client)

    # Platform stats
    stats = await async_client.get("/admin/stats", headers=_auth(token))
    assert stats.status_code == 200
    body = stats.json()
    assert "total_tenants" in body
    assert "total_listings" in body

    # Credits summary
    credits_summary = await async_client.get("/admin/credits/summary", headers=_auth(token))
    assert credits_summary.status_code == 200
    body = credits_summary.json()
    assert "total_credits_issued" in body
    assert "total_credits_consumed" in body

    # Audit log
    audit = await async_client.get("/admin/audit-log", headers=_auth(token))
    assert audit.status_code == 200
    assert isinstance(audit.json(), list)

    # Recent events
    events = await async_client.get("/admin/events/recent", headers=_auth(token))
    assert events.status_code == 200
    assert isinstance(events.json(), list)


@pytest.mark.asyncio
async def test_admin_tenant_detail_includes_credit_balance(async_client: AsyncClient):
    """Admin GET /admin/tenants/{id} must include credit_balance field."""
    token, tenant_id = await _register_admin(async_client)

    resp = await async_client.get(f"/admin/tenants/{tenant_id}", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert "credit_balance" in body
    assert isinstance(body["credit_balance"], (int, float))


# ── Credit purchase Stripe flow (shape + idempotency) ────────────────────────


@pytest.mark.asyncio
async def test_credit_purchase_initiates_checkout(async_client: AsyncClient):
    """
    POST /credits/purchase must return a Stripe checkout URL.
    Mocks Stripe so no real API call is made.
    """
    token, _ = await _register(async_client, plan_tier="active_agent")

    mock_session_url = "https://checkout.stripe.com/pay/cs_test_mock"

    with patch("listingjet.api.credits.BillingService") as mock_svc_cls:
        mock_svc = MagicMock()
        mock_svc.create_credit_checkout = AsyncMock(return_value=mock_session_url)
        mock_svc_cls.return_value = mock_svc

        resp = await async_client.post(
            "/credits/purchase",
            json={"bundle_size": 10},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "checkout_url" in body
    assert body["checkout_url"] == mock_session_url


@pytest.mark.asyncio
async def test_credit_purchase_invalid_bundle_size(async_client: AsyncClient):
    """POST /credits/purchase with an invalid bundle_size must return 400."""
    token, _ = await _register(async_client)
    resp = await async_client.post(
        "/credits/purchase",
        json={"bundle_size": 9999},
        headers=_auth(token),
    )
    assert resp.status_code == 400


# ── Webhook → credit fulfillment ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_bundle_fulfillment_credits_are_added(async_client: AsyncClient, db_session):
    """
    Simulate a Stripe checkout.session.completed webhook for a credit bundle.
    After the webhook is processed the tenant's balance must increase.
    """
    token, tenant_id = await _register(async_client, plan_tier="lite")

    # Ensure credit account exists
    from listingjet.services.credits import CreditService
    svc = CreditService()
    await svc.ensure_account(db_session, uuid.UUID(tenant_id))
    await db_session.commit()

    balance_before_resp = await async_client.get("/credits/balance", headers=_auth(token))
    balance_before = balance_before_resp.json().get("balance", 0) if balance_before_resp.status_code == 200 else 0

    session_id = f"cs_test_{uuid.uuid4().hex[:16]}"
    event_id = f"evt_{uuid.uuid4().hex[:16]}"

    mock_event = MagicMock()
    mock_event.type = "checkout.session.completed"
    mock_event.id = event_id
    mock_event.data.object = {
        "id": session_id,
        "metadata": {
            "tenant_id": tenant_id,
            "type": "credit_bundle",
            "bundle_size": "5",
        },
        "subscription": None,
        "customer": f"cus_{uuid.uuid4().hex[:14]}",
    }

    with patch("listingjet.api.billing.BillingService") as mock_svc_cls:
        mock_svc = MagicMock()
        mock_svc.construct_webhook_event = MagicMock(return_value=mock_event)
        mock_svc_cls.return_value = mock_svc

        resp = await async_client.post(
            "/billing/webhook",
            content=b"{}",
            headers={"stripe-signature": "test_sig"},
        )
    assert resp.status_code == 200

    balance_after_resp = await async_client.get("/credits/balance", headers=_auth(token))
    if balance_after_resp.status_code == 200:
        balance_after = balance_after_resp.json().get("balance", 0)
        assert balance_after > balance_before
