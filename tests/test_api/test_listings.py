# tests/test_api/test_listings.py
import uuid
import pytest
import jwt as pyjwt
from httpx import AsyncClient
from launchlens.config import settings


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
async def test_create_listing(async_client: AsyncClient):
    token, _ = await _register(async_client)
    resp = await async_client.post("/listings", json={
        "address": {"street": "100 Main St", "city": "Austin", "state": "TX", "zip": "78701"},
        "metadata": {"beds": 3, "baths": 2, "sqft": 1500, "price": 350000},
    }, headers=_auth(token))
    assert resp.status_code == 201
    body = resp.json()
    assert body["state"] == "new"
    assert body["address"]["city"] == "Austin"
    assert "id" in body


@pytest.mark.asyncio
async def test_list_listings_empty(async_client: AsyncClient):
    token, _ = await _register(async_client)
    resp = await async_client.get("/listings", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_listings_returns_own(async_client: AsyncClient):
    token, _ = await _register(async_client)
    await async_client.post("/listings", json={
        "address": {"street": "1 A St"}, "metadata": {"beds": 1},
    }, headers=_auth(token))
    resp = await async_client.get("/listings", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_list_listings_tenant_isolation(async_client: AsyncClient):
    token_a, _ = await _register(async_client)
    token_b, _ = await _register(async_client)
    await async_client.post("/listings", json={
        "address": {"street": "A St"}, "metadata": {},
    }, headers=_auth(token_a))
    resp = await async_client.get("/listings", headers=_auth(token_b))
    assert resp.json() == []


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
