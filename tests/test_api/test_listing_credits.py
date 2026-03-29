"""Listing creation/cancel with credit billing — deduction, insufficient, legacy, refund."""
import uuid

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from listingjet.config import settings


async def _register(client: AsyncClient) -> tuple[str, str]:
    email = f"listcred-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "CreditUser", "company_name": "CreditCo"
    })
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _set_credit_billing(db_session, tenant_id: str, credits: int = 10, cost: int = 1):
    """Switch tenant to credit billing and fund their account."""
    from listingjet.models.tenant import Tenant
    from listingjet.services.credits import CreditService

    tid = uuid.UUID(tenant_id)
    tenant = await db_session.get(Tenant, tid)
    tenant.billing_model = "credit"
    tenant.per_listing_credit_cost = cost
    await db_session.flush()

    svc = CreditService()
    await svc.ensure_account(db_session, tid)
    if credits > 0:
        await svc.add_credits(
            db_session, tid, credits,
            transaction_type="purchase",
            reference_id=str(uuid.uuid4()),
        )
    await db_session.commit()


# --- Credit deduction on listing creation ---


@pytest.mark.asyncio
async def test_create_listing_credit_deduction(async_client: AsyncClient, db_session):
    token, tenant_id = await _register(async_client)
    await _set_credit_billing(db_session, tenant_id, credits=10, cost=1)

    resp = await async_client.post("/listings", json={
        "address": {"street": "1 Credit Ave"},
        "metadata": {},
    }, headers=_auth(token))
    assert resp.status_code == 201

    # Balance should be 9 (10 - 1)
    bal = await async_client.get("/credits/balance", headers=_auth(token))
    assert bal.json()["balance"] == 9


@pytest.mark.asyncio
async def test_create_listing_insufficient_credits_402(async_client: AsyncClient, db_session):
    token, tenant_id = await _register(async_client)
    await _set_credit_billing(db_session, tenant_id, credits=0, cost=1)

    resp = await async_client.post("/listings", json={
        "address": {"street": "1 Broke St"},
        "metadata": {},
    }, headers=_auth(token))
    assert resp.status_code == 402
    assert "Insufficient credits" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_listing_legacy_billing_unchanged(async_client: AsyncClient, db_session):
    """Legacy (non-credit) billing still uses monthly quota, not credits."""
    token, tenant_id = await _register(async_client)
    # Default billing_model is "credit" per migration, but new tenants via register
    # may default differently. Set explicitly to legacy.
    from listingjet.models.tenant import Tenant
    tenant = await db_session.get(Tenant, uuid.UUID(tenant_id))
    tenant.billing_model = "legacy"
    await db_session.commit()

    resp = await async_client.post("/listings", json={
        "address": {"street": "1 Legacy Blvd"},
        "metadata": {},
    }, headers=_auth(token))
    # Should succeed via quota (starter plan allows 5/month)
    assert resp.status_code == 201


# --- Cancel listing refunds credits ---


@pytest.mark.asyncio
async def test_cancel_listing_refunds_credits(async_client: AsyncClient, db_session):
    token, tenant_id = await _register(async_client)
    await _set_credit_billing(db_session, tenant_id, credits=10, cost=2)

    # Create listing — costs 2 credits
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "1 Cancel Rd"},
        "metadata": {},
    }, headers=_auth(token))
    assert create_resp.status_code == 201
    listing_id = create_resp.json()["id"]

    bal_after_create = (await async_client.get("/credits/balance", headers=_auth(token))).json()["balance"]
    assert bal_after_create == 8

    # Cancel — should refund 2 credits
    cancel_resp = await async_client.post(f"/listings/{listing_id}/cancel", headers=_auth(token))
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["credits_refunded"] == 2

    bal_after_cancel = (await async_client.get("/credits/balance", headers=_auth(token))).json()["balance"]
    assert bal_after_cancel == 10


@pytest.mark.asyncio
async def test_cancel_listing_no_refund_legacy(async_client: AsyncClient, db_session):
    """Legacy billing cancel doesn't refund credits."""
    token, tenant_id = await _register(async_client)
    from listingjet.models.tenant import Tenant
    tenant = await db_session.get(Tenant, uuid.UUID(tenant_id))
    tenant.billing_model = "legacy"
    await db_session.commit()

    create_resp = await async_client.post("/listings", json={
        "address": {"street": "1 Legacy Cancel Blvd"},
        "metadata": {},
    }, headers=_auth(token))
    assert create_resp.status_code == 201
    listing_id = create_resp.json()["id"]

    cancel_resp = await async_client.post(f"/listings/{listing_id}/cancel", headers=_auth(token))
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["credits_refunded"] == 0
