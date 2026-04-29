# tests/test_api/test_listings.py
import uuid

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from listingjet.config import settings
from listingjet.models.listing import ListingState


async def _register(client: AsyncClient) -> tuple[str, str]:
    email = f"test-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Tester", "company_name": "TestCo",
        "plan_tier": "free",
    })
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_listing(async_client: AsyncClient):
    token, _ = await _register(async_client)
    resp = await async_client.post("/listings", json={
        "address": {"street": "100 Main St", "city": "Austin", "state": "TX", "zip": "78701"},
        "metadata": {"beds": 3, "baths": 2, "sqft": 1500, "price": 350000},
    }, headers=_auth(token))
    assert resp.status_code == 201
    body = resp.json()
    assert body["state"] == "draft"
    assert body["address"]["city"] == "Austin"
    assert "id" in body


@pytest.mark.asyncio
async def test_list_listings_empty(async_client: AsyncClient):
    token, _ = await _register(async_client)
    resp = await async_client.get("/listings", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_list_listings_returns_own(async_client: AsyncClient):
    token, _ = await _register(async_client)
    await async_client.post("/listings", json={
        "address": {"street": "1 A St"}, "metadata": {"beds": 1},
    }, headers=_auth(token))
    resp = await async_client.get("/listings?state=draft", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1


@pytest.mark.asyncio
async def test_list_listings_tenant_isolation(async_client: AsyncClient):
    token_a, _ = await _register(async_client)
    token_b, _ = await _register(async_client)
    await async_client.post("/listings", json={
        "address": {"street": "A St"}, "metadata": {},
    }, headers=_auth(token_a))
    resp = await async_client.get("/listings", headers=_auth(token_b))
    body = resp.json()
    assert body["items"] == []


@pytest.mark.asyncio
async def test_create_listing_requires_auth(async_client: AsyncClient):
    resp = await async_client.post("/listings", json={"address": {}, "metadata": {}})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_listing_detail(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "200 Oak Ln"}, "metadata": {"beds": 4},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    resp = await async_client.get(f"/listings/{listing_id}", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["id"] == listing_id
    assert resp.json()["address"]["street"] == "200 Oak Ln"


@pytest.mark.asyncio
async def test_get_listing_not_found(async_client: AsyncClient):
    token, _ = await _register(async_client)
    resp = await async_client.get(f"/listings/{uuid.uuid4()}", headers=_auth(token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_listing_cross_tenant_404(async_client: AsyncClient):
    token_a, _ = await _register(async_client)
    token_b, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Secret St"}, "metadata": {},
    }, headers=_auth(token_a))
    listing_id = create_resp.json()["id"]
    resp = await async_client.get(f"/listings/{listing_id}", headers=_auth(token_b))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_listing(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Old St"}, "metadata": {"beds": 2},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    resp = await async_client.patch(f"/listings/{listing_id}", json={
        "address": {"street": "New St", "city": "Denver"},
    }, headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["address"]["street"] == "New St"


@pytest.mark.asyncio
async def test_update_listing_metadata_only(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Keep St"}, "metadata": {"beds": 2},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    resp = await async_client.patch(f"/listings/{listing_id}", json={
        "metadata": {"beds": 3, "baths": 2},
    }, headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["metadata"]["beds"] == 3
    assert resp.json()["address"]["street"] == "Keep St"


@pytest.mark.asyncio
async def test_get_package_empty(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Pkg St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    resp = await async_client.get(f"/listings/{listing_id}/package", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_start_review(async_client: AsyncClient, db_session):
    token, tenant_id = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Review St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    from sqlalchemy import update

    from listingjet.models.listing import Listing
    await db_session.execute(
        update(Listing).where(Listing.id == uuid.UUID(listing_id)).values(state=ListingState.AWAITING_REVIEW)
    )
    await db_session.commit()

    resp = await async_client.post(f"/listings/{listing_id}/review", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["state"] == "in_review"


@pytest.mark.asyncio
async def test_approve_listing(async_client: AsyncClient, db_session):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Approve St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    from sqlalchemy import update

    from listingjet.models.listing import Listing
    await db_session.execute(
        update(Listing).where(Listing.id == uuid.UUID(listing_id)).values(state=ListingState.IN_REVIEW)
    )
    await db_session.commit()

    resp = await async_client.post(f"/listings/{listing_id}/approve", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["state"] == "approved"


@pytest.mark.asyncio
async def test_approve_wrong_state_returns_409(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Bad Approve St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]
    resp = await async_client.post(f"/listings/{listing_id}/approve", headers=_auth(token))
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_review_wrong_state_returns_409(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Bad Review St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]
    resp = await async_client.post(f"/listings/{listing_id}/review", headers=_auth(token))
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_retry_listing_wrong_state_returns_409(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Retry St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]
    # NEW state is not retryable
    resp = await async_client.post(f"/listings/{listing_id}/retry", headers=_auth(token))
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_retry_failed_listing(async_client: AsyncClient, db_session):
    from listingjet.models.listing import Listing

    token, tenant_id = await _register(async_client)

    # Create a listing then set it to FAILED directly in DB
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Failed St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    listing = await db_session.get(Listing, uuid.UUID(listing_id))
    listing.state = ListingState.FAILED
    await db_session.commit()

    resp = await async_client.post(f"/listings/{listing_id}/retry", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "uploading"


@pytest.mark.asyncio
async def test_reorder_package_swaps_positions(async_client: AsyncClient, db_session):
    """Reorder swap must succeed despite the unique(listing_id, channel, position)
    constraint. Direct in-place swap violated it mid-flush; the staged-via-NULL
    fix must produce a clean final state with positions exchanged."""
    from listingjet.models.listing import Listing
    from listingjet.models.package_selection import PackageSelection

    token, tenant_id = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Reorder St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]
    listing_uuid = uuid.UUID(listing_id)
    tenant_uuid = uuid.UUID(tenant_id)

    listing = await db_session.get(Listing, listing_uuid)
    listing.state = ListingState.AWAITING_REVIEW

    asset_a, asset_b = uuid.uuid4(), uuid.uuid4()
    db_session.add_all([
        PackageSelection(
            id=uuid.uuid4(), tenant_id=tenant_uuid, listing_id=listing_uuid,
            asset_id=asset_a, channel="mls", position=0, selected_by="ai",
            composite_score=0.9,
        ),
        PackageSelection(
            id=uuid.uuid4(), tenant_id=tenant_uuid, listing_id=listing_uuid,
            asset_id=asset_b, channel="mls", position=1, selected_by="ai",
            composite_score=0.8,
        ),
    ])
    await db_session.commit()

    resp = await async_client.post(
        f"/listings/{listing_id}/package/reorder",
        json={"swaps": [{"from_position": 0, "to_position": 1}]},
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["swaps_applied"] == 1

    await db_session.commit()  # drop any cached state
    rows = (await db_session.execute(
        PackageSelection.__table__.select().where(
            PackageSelection.listing_id == listing_uuid
        )
    )).all()
    by_asset = {r.asset_id: r.position for r in rows}
    assert by_asset[asset_a] == 1
    assert by_asset[asset_b] == 0
