"""Tests for admin credit management endpoints."""

import uuid

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from listingjet.config import settings


async def _register_admin(client: AsyncClient) -> tuple[str, str]:
    """Register a superadmin user, return (token, tenant_id)."""
    from tests.conftest import promote_to_superadmin
    email = f"admin-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "AdminPass1!", "name": "Admin", "company_name": "AdminCo"
    })
    token = resp.json()["access_token"]
    await promote_to_superadmin(client, token)
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_tenant_credits_empty(async_client: AsyncClient):
    token, tenant_id = await _register_admin(async_client)
    resp = await async_client.get(f"/admin/tenants/{tenant_id}/credits", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == tenant_id
    assert body["credit_balance"] == 0
    assert body["transactions"] == []


@pytest.mark.asyncio
async def test_adjust_credits_add(async_client: AsyncClient):
    token, tenant_id = await _register_admin(async_client)
    resp = await async_client.post(
        f"/admin/tenants/{tenant_id}/credits/adjust",
        json={"amount": 10, "reason": "Welcome bonus"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["amount"] == 10
    assert body["balance_after"] == 10
    assert body["transaction_type"] == "admin_adjustment"
    assert body["description"] == "Welcome bonus"


@pytest.mark.asyncio
async def test_adjust_credits_deduct(async_client: AsyncClient):
    token, tenant_id = await _register_admin(async_client)
    # Add first
    await async_client.post(
        f"/admin/tenants/{tenant_id}/credits/adjust",
        json={"amount": 20, "reason": "Initial"},
        headers=_auth(token),
    )
    # Deduct
    resp = await async_client.post(
        f"/admin/tenants/{tenant_id}/credits/adjust",
        json={"amount": -5, "reason": "Correction"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["balance_after"] == 15


@pytest.mark.asyncio
async def test_adjust_credits_prevents_negative_balance(async_client: AsyncClient):
    token, tenant_id = await _register_admin(async_client)
    resp = await async_client.post(
        f"/admin/tenants/{tenant_id}/credits/adjust",
        json={"amount": -5, "reason": "Over-deduct"},
        headers=_auth(token),
    )
    assert resp.status_code == 400
    assert "negative balance" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_adjust_credits_zero_rejected(async_client: AsyncClient):
    token, tenant_id = await _register_admin(async_client)
    resp = await async_client.post(
        f"/admin/tenants/{tenant_id}/credits/adjust",
        json={"amount": 0, "reason": "Nothing"},
        headers=_auth(token),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_credits_summary(async_client: AsyncClient):
    token, tenant_id = await _register_admin(async_client)
    # Add some credits
    await async_client.post(
        f"/admin/tenants/{tenant_id}/credits/adjust",
        json={"amount": 50, "reason": "Test"},
        headers=_auth(token),
    )

    resp = await async_client.get("/admin/credits/summary", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_credits_outstanding"] >= 50
    assert "credits_purchased_this_month" in body
    assert "credits_used_this_month" in body
    assert "credits_adjusted_this_month" in body
    assert "tenant_count_with_credits" in body


@pytest.mark.asyncio
async def test_tenant_credits_shows_transactions(async_client: AsyncClient):
    token, tenant_id = await _register_admin(async_client)
    # Make two adjustments
    await async_client.post(
        f"/admin/tenants/{tenant_id}/credits/adjust",
        json={"amount": 10, "reason": "First"},
        headers=_auth(token),
    )
    await async_client.post(
        f"/admin/tenants/{tenant_id}/credits/adjust",
        json={"amount": 5, "reason": "Second"},
        headers=_auth(token),
    )

    resp = await async_client.get(f"/admin/tenants/{tenant_id}/credits", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["credit_balance"] == 15
    assert len(body["transactions"]) == 2
    # Most recent first — the admin schema uses "description" not "reason"
    assert body["transactions"][0]["description"] == "Second"
    assert body["transactions"][1]["description"] == "First"


@pytest.mark.asyncio
async def test_revenue_breakdown(async_client: AsyncClient):
    token, _ = await _register_admin(async_client)
    resp = await async_client.get("/admin/analytics/revenue", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert "subscription_tenant_count" in body
    assert "credit_purchase_count" in body
    assert "total_credits_purchased" in body
    assert "top_tenants_by_usage" in body
    assert "avg_credits_per_listing" in body


@pytest.mark.asyncio
async def test_tenant_list_includes_credit_balance(async_client: AsyncClient):
    token, tenant_id = await _register_admin(async_client)
    # Add credits
    await async_client.post(
        f"/admin/tenants/{tenant_id}/credits/adjust",
        json={"amount": 25, "reason": "Test"},
        headers=_auth(token),
    )

    resp = await async_client.get("/admin/tenants", headers=_auth(token))
    assert resp.status_code == 200
    tenants = resp.json()
    tenant = next(t for t in tenants if t["id"] == tenant_id)
    assert tenant["credit_balance"] == 25
