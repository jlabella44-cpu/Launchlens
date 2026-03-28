# tests/test_api/test_dollhouse.py
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
async def test_get_dollhouse_not_ready(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "No Floor St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    resp = await async_client.get(f"/listings/{listing_id}/dollhouse", headers=_auth(token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_dollhouse_requires_auth(async_client: AsyncClient):
    resp = await async_client.get(f"/listings/{uuid.uuid4()}/dollhouse")
    assert resp.status_code == 401
