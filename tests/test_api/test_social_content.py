import json
import uuid

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from listingjet.config import settings
from listingjet.models.social_content import SocialContent


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


async def _create_listing(client: AsyncClient, token: str) -> str:
    resp = await client.post("/listings", json={
        "address": {"street": "123 Social St"}, "metadata": {},
    }, headers=_auth(token))
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_social_content_with_rows(async_client: AsyncClient, db_session):
    token, tenant_id = await _register(async_client)
    listing_id = await _create_listing(async_client, token)

    instagram_hooks = [
        {"style": "storyteller", "caption": "Once upon a time, a home..."},
        {"style": "data_driven", "caption": "3 beds, 2 baths, 1800 sqft."},
        {"style": "luxury_minimalist", "caption": "Refined living."},
        {"style": "urgency", "caption": "Won't last long."},
        {"style": "lifestyle", "caption": "Weekend mornings on the porch."},
    ]
    facebook_hooks = [
        {"style": "storyteller", "caption": "fb storyteller"},
        {"style": "data_driven", "caption": "fb data driven"},
        {"style": "luxury_minimalist", "caption": "fb luxury"},
        {"style": "urgency", "caption": "fb urgency"},
        {"style": "lifestyle", "caption": "fb lifestyle"},
    ]

    db_session.add_all([
        SocialContent(
            tenant_id=tenant_id,
            listing_id=listing_id,
            platform="instagram",
            caption=json.dumps(instagram_hooks),
            hashtags=["#dreamhome", "#realestate"],
            cta="DM us for a showing!",
        ),
        SocialContent(
            tenant_id=tenant_id,
            listing_id=listing_id,
            platform="facebook",
            caption=json.dumps(facebook_hooks),
            hashtags=None,
            cta="Message us today!",
        ),
        SocialContent(
            tenant_id=tenant_id,
            listing_id=listing_id,
            platform="tiktok",
            caption="Check out this listing!",
            hashtags=None,
            cta=None,
        ),
    ])
    await db_session.commit()

    resp = await async_client.get(f"/listings/{listing_id}/social-content", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["instagram_captions"]["storyteller"] == "Once upon a time, a home..."
    assert len(body["facebook_captions"]) == 5
    assert body["hashtags"] == ["#dreamhome", "#realestate"]
    assert body["tiktok_caption"] == "Check out this listing!"
    assert body["cta"]["instagram"] == "DM us for a showing!"
    assert body["cta"]["facebook"] == "Message us today!"
    assert body["generated"] is True


@pytest.mark.asyncio
async def test_social_content_no_rows(async_client: AsyncClient):
    token, _ = await _register(async_client)
    listing_id = await _create_listing(async_client, token)

    resp = await async_client.get(f"/listings/{listing_id}/social-content", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["instagram_captions"] == {}
    assert body["facebook_captions"] == {}
    assert body["tiktok_caption"] is None
    assert body["hashtags"] == []
    assert body["generated"] is False


@pytest.mark.asyncio
async def test_social_content_cross_tenant_404(async_client: AsyncClient):
    token_a, _ = await _register(async_client)
    listing_id = await _create_listing(async_client, token_a)

    token_b, _ = await _register(async_client)

    resp = await async_client.get(f"/listings/{listing_id}/social-content", headers=_auth(token_b))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_social_content_legacy_plain_text_caption(async_client: AsyncClient, db_session):
    token, tenant_id = await _register(async_client)
    listing_id = await _create_listing(async_client, token)

    db_session.add(SocialContent(
        tenant_id=tenant_id,
        listing_id=listing_id,
        platform="instagram",
        caption="A plain legacy caption, not JSON.",
        hashtags=None,
        cta=None,
    ))
    await db_session.commit()

    resp = await async_client.get(f"/listings/{listing_id}/social-content", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["instagram_captions"] == {"storyteller": "A plain legacy caption, not JSON."}
