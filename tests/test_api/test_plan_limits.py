# tests/test_api/test_plan_limits.py
import uuid

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from listingjet.config import settings
from listingjet.services.plan_limits import PLAN_LIMITS, get_limits


def test_plan_limits_has_all_tiers():
    assert "starter" in PLAN_LIMITS
    assert "pro" in PLAN_LIMITS
    assert "enterprise" in PLAN_LIMITS


def test_starter_limits():
    limits = get_limits("starter")
    assert limits["max_listings_per_month"] == 5
    assert limits["max_assets_per_listing"] == 25
    assert limits["tier2_vision"] is False


def test_pro_limits():
    limits = get_limits("pro")
    assert limits["max_listings_per_month"] == 50
    assert limits["max_assets_per_listing"] == 50
    assert limits["tier2_vision"] is True


def test_enterprise_limits():
    limits = get_limits("enterprise")
    assert limits["max_listings_per_month"] == 500
    assert limits["tier2_vision"] is True


def test_unknown_plan_returns_starter():
    limits = get_limits("unknown")
    assert limits["max_listings_per_month"] == 5


def test_check_listing_quota_under_limit():
    from listingjet.services.plan_limits import check_listing_quota
    assert check_listing_quota("starter", current_count=3) is True


def test_check_listing_quota_at_limit():
    from listingjet.services.plan_limits import check_listing_quota
    assert check_listing_quota("starter", current_count=5) is False


def test_check_asset_quota_under_limit():
    from listingjet.services.plan_limits import check_asset_quota
    assert check_asset_quota("starter", existing_count=10, adding_count=10) is True


def test_check_asset_quota_over_limit():
    from listingjet.services.plan_limits import check_asset_quota
    assert check_asset_quota("starter", existing_count=10, adding_count=20) is False


async def _register(client: AsyncClient) -> tuple[str, str]:
    email = f"test-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Tester", "company_name": "TestCo"
    })
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_listing_enforces_monthly_quota(async_client: AsyncClient):
    """Starter plan: 5 listings/month. 6th should return 403."""
    token, _ = await _register(async_client)
    for i in range(5):
        resp = await async_client.post("/listings", json={
            "address": {"street": f"{i} Quota St"}, "metadata": {},
        }, headers=_auth(token))
        assert resp.status_code == 201, f"Listing {i+1} should succeed"

    resp = await async_client.post("/listings", json={
        "address": {"street": "6 Quota St"}, "metadata": {},
    }, headers=_auth(token))
    assert resp.status_code == 403
    assert "limit" in resp.json()["detail"].lower() or "upgrade" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_assets_enforces_per_listing_quota(async_client: AsyncClient):
    """Starter plan: 25 assets/listing. Adding beyond limit returns 403."""
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Asset Quota St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    assets_batch = [{"file_path": f"s3://b/{i}.jpg", "file_hash": f"h{i:03d}"} for i in range(25)]
    resp = await async_client.post(f"/listings/{listing_id}/assets", json={
        "assets": assets_batch
    }, headers=_auth(token))
    assert resp.status_code == 201

    resp = await async_client.post(f"/listings/{listing_id}/assets", json={
        "assets": [{"file_path": "s3://b/extra.jpg", "file_hash": "hextra"}]
    }, headers=_auth(token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_listing_allowed_under_quota(async_client: AsyncClient):
    """First listing for a new tenant should always succeed."""
    token, _ = await _register(async_client)
    resp = await async_client.post("/listings", json={
        "address": {"street": "OK St"}, "metadata": {},
    }, headers=_auth(token))
    assert resp.status_code == 201
