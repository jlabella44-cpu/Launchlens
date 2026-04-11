"""Superadmin gate on CMA endpoints.

The CMA feature currently runs on the synthetic-comparables fallback path
because Repliers ($200/mo minimum) isn't activated yet. Until it is, the
endpoints are superadmin-only so staff can demo/QA without exposing
unverified comps to paying tenants.
"""
import uuid

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from listingjet.config import settings
from tests.conftest import promote_to_superadmin


async def _register(client: AsyncClient) -> tuple[str, str]:
    """Register a fresh user and return (token, tenant_id). Still regular role."""
    email = f"cma-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email,
        "password": "CmaPass1!",
        "name": "CMA User",
        "company_name": "CmaCo",
        "plan_tier": "free",
    })
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_generate_cma_report_requires_superadmin(async_client: AsyncClient):
    """Regular tenant admins (the default registered role) get 403."""
    token, _tenant_id = await _register(async_client)
    listing_id = uuid.uuid4()

    resp = await async_client.post(
        f"/listings/{listing_id}/cma-report",
        headers=_auth(token),
    )
    assert resp.status_code == 403
    assert "admin" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_cma_report_requires_superadmin(async_client: AsyncClient):
    """Non-superadmins can't read CMA reports either."""
    token, _tenant_id = await _register(async_client)
    listing_id = uuid.uuid4()

    resp = await async_client.get(
        f"/listings/{listing_id}/cma-report",
        headers=_auth(token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_cma_endpoints_reject_unauthenticated(async_client: AsyncClient):
    listing_id = uuid.uuid4()
    post_resp = await async_client.post(f"/listings/{listing_id}/cma-report")
    get_resp = await async_client.get(f"/listings/{listing_id}/cma-report")
    assert post_resp.status_code in (401, 403)
    assert get_resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_superadmin_gets_past_gate_on_get(async_client: AsyncClient):
    """Superadmin role passes the auth gate. No report exists yet → 404 (not 403)."""
    token, _tenant_id = await _register(async_client)
    await promote_to_superadmin(async_client, token)
    listing_id = uuid.uuid4()

    resp = await async_client.get(
        f"/listings/{listing_id}/cma-report",
        headers=_auth(token),
    )
    # The key assertion: NOT 403. A 404 means the gate let us through and
    # we hit the "no report found" branch, which is the expected path for a
    # fresh listing_id with no CMA generated yet.
    assert resp.status_code == 404
