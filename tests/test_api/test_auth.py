# tests/test_api/test_auth.py
import uuid

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from listingjet.models.user import User, UserRole
from listingjet.services.auth import create_access_token, decode_token, hash_password, verify_password


def test_user_model_has_password_hash():
    """User model must have a password_hash field."""
    annotations = {}
    for cls in reversed(User.__mro__):
        if hasattr(cls, '__annotations__'):
            annotations.update(cls.__annotations__)
    assert "password_hash" in annotations, "User model missing password_hash field"


def test_hash_password_produces_different_hashes():
    h1 = hash_password("secret")
    h2 = hash_password("secret")
    assert h1 != h2  # bcrypt salts each hash


def test_verify_password_correct():
    h = hash_password("mypassword")
    assert verify_password("mypassword", h) is True


def test_verify_password_wrong():
    h = hash_password("mypassword")
    assert verify_password("wrong", h) is False


def test_create_and_decode_token():
    user = User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="x@example.com",
        password_hash="x",
        role=UserRole.ADMIN,
    )
    token = create_access_token(user)
    payload = decode_token(token)
    assert payload["sub"] == str(user.id)
    assert payload["tenant_id"] == str(user.tenant_id)
    assert payload["role"] == UserRole.ADMIN.value


def test_decode_token_invalid_raises():
    with pytest.raises(HTTPException) as exc_info:
        decode_token("not.a.valid.token")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_register_creates_user_and_returns_token(async_client: AsyncClient):
    email = f"test-{uuid.uuid4()}@example.com"
    resp = await async_client.post("/auth/register", json={
        "email": email,
        "password": "StrongPass1!",
        "name": "Alice Smith",
        "company_name": "Acme Realty",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(async_client: AsyncClient):
    email = f"test-{uuid.uuid4()}@example.com"
    payload = {"email": email, "password": "StrongPass1!", "name": "Bob", "company_name": "Corp"}
    await async_client.post("/auth/register", json=payload)
    resp = await async_client.post("/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient):
    email = f"test-{uuid.uuid4()}@example.com"
    await async_client.post("/auth/register", json={
        "email": email, "password": "MyPass123!", "name": "Carol", "company_name": "Homes Inc"
    })
    resp = await async_client.post("/auth/login", json={"email": email, "password": "MyPass123!"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(async_client: AsyncClient):
    email = f"test-{uuid.uuid4()}@example.com"
    await async_client.post("/auth/register", json={
        "email": email, "password": "CorrectPass1!", "name": "Dave", "company_name": "Listings Co"
    })
    resp = await async_client.post("/auth/login", json={"email": email, "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(async_client: AsyncClient):
    resp = await async_client.post("/auth/login", json={
        "email": f"ghost-{uuid.uuid4()}@example.com",
        "password": "anything",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_valid_token(async_client: AsyncClient):
    """A token from /auth/login should work as Bearer on a protected route."""
    email = f"test-{uuid.uuid4()}@example.com"
    reg = await async_client.post("/auth/register", json={
        "email": email, "password": "ValidPass1!", "name": "Eve", "company_name": "Eve Corp"
    })
    token = reg.json()["access_token"]
    resp = await async_client.get("/listings", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_missing_token_returns_401(async_client: AsyncClient):
    resp = await async_client.get("/listings")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_returns_401(async_client: AsyncClient):
    resp = await async_client.get("/listings", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_returns_current_user(async_client: AsyncClient):
    """GET /auth/me returns the authenticated user's profile."""
    email = f"test-{uuid.uuid4()}@example.com"
    reg = await async_client.post("/auth/register", json={
        "email": email, "password": "ValidPass1!", "name": "Frank", "company_name": "Frank LLC"
    })
    token = reg.json()["access_token"]
    resp = await async_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == email
    assert body["role"] == UserRole.ADMIN.value


@pytest.mark.asyncio
async def test_admin_only_endpoint_rejects_non_admin(async_client: AsyncClient, db_session):
    """Admin-only route should return 403 for non-admin users."""
    from listingjet.models.tenant import Tenant
    from listingjet.services.auth import create_access_token, hash_password

    # Create a viewer user directly in DB
    tenant = Tenant(id=uuid.uuid4(), name="ViewerCo", plan="starter")
    db_session.add(tenant)
    await db_session.flush()

    viewer = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"viewer-{uuid.uuid4()}@example.com",
        password_hash=hash_password("TestPass1!"),
        name="Viewer",
        role=UserRole.VIEWER,
    )
    db_session.add(viewer)
    await db_session.commit()

    viewer_token = create_access_token(viewer)
    resp = await async_client.get("/admin/health", headers={"Authorization": f"Bearer {viewer_token}"})
    assert resp.status_code == 403
