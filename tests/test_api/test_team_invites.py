"""Tests for the team invite-token flow.

Covers:
  POST /team/members           — admin invites a new member; pending user row
                                 created with null password; email sent
  GET  /auth/invite/{token}    — public invite lookup (email, tenant name)
  POST /auth/accept-invite     — invitee sets password, consumes token, logs in
  GET  /team/members           — pending_invite flag on listed users
  POST /auth/login             — rejected for users with null password_hash
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from listingjet.config import settings
from listingjet.models.user import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_admin(client: AsyncClient) -> tuple[str, str, str]:
    """Register a tenant admin user. Returns (token, tenant_id, email)."""
    email = f"owner-{uuid.uuid4()}@example.com"
    resp = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "OwnerPass1!",
            "name": "Owner",
            "company_name": "OwnerCo",
            "plan_tier": "free",
        },
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"], email


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def mock_email_service():
    """Replace the email service with a no-op so tests don't hit SMTP/SES."""
    svc = MagicMock()
    svc.send_notification = MagicMock()
    svc.send = MagicMock()
    with patch("listingjet.api.team.get_email_service", return_value=svc):
        yield svc


# ---------------------------------------------------------------------------
# POST /team/members — sending an invitation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invite_creates_pending_user_with_no_password(
    async_client: AsyncClient, mock_email_service, db_session
):
    token, tenant_id, _ = await _register_admin(async_client)

    resp = await async_client.post(
        "/team/members",
        json={"email": "new@example.com", "name": "New Person", "role": "agent"},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "new@example.com"
    assert body["name"] == "New Person"
    assert body["role"] == "agent"
    assert "invite_expires_at" in body

    # Pending row in DB: no password, has token hash, expires in the future
    invited = (
        await db_session.execute(
            select(User).where(User.email == "new@example.com")
        )
    ).scalar_one()
    assert invited.password_hash is None
    assert invited.invite_token_hash is not None
    assert invited.invite_expires_at is not None
    assert invited.invite_expires_at > datetime.now(timezone.utc)
    assert str(invited.tenant_id) == tenant_id
    assert invited.role.value == "agent"


@pytest.mark.asyncio
async def test_invite_sends_email(async_client: AsyncClient, mock_email_service):
    token, _tenant_id, _ = await _register_admin(async_client)

    resp = await async_client.post(
        "/team/members",
        json={"email": "mail-test@example.com", "role": "agent"},
        headers=_auth(token),
    )
    assert resp.status_code == 201

    mock_email_service.send_notification.assert_called_once()
    args, kwargs = mock_email_service.send_notification.call_args
    # First positional arg is the recipient email
    assert args[0] == "mail-test@example.com"
    assert args[1] == "team_member_invite"
    assert "accept_url" in kwargs
    assert "/accept-invite?token=" in kwargs["accept_url"]
    assert kwargs["tenant_name"] == "OwnerCo"


@pytest.mark.asyncio
async def test_invite_duplicate_email_rejected(
    async_client: AsyncClient, mock_email_service
):
    token, _tenant_id, owner_email = await _register_admin(async_client)

    # Inviting with the owner's own email should conflict
    resp = await async_client.post(
        "/team/members",
        json={"email": owner_email, "role": "agent"},
        headers=_auth(token),
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_invite_invalid_role_rejected(
    async_client: AsyncClient, mock_email_service
):
    token, _tenant_id, _ = await _register_admin(async_client)

    resp = await async_client.post(
        "/team/members",
        json={"email": "bad-role@example.com", "role": "potato"},
        headers=_auth(token),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_invite_cannot_escalate_to_superadmin(
    async_client: AsyncClient, mock_email_service
):
    token, _tenant_id, _ = await _register_admin(async_client)

    resp = await async_client.post(
        "/team/members",
        json={"email": "escalation@example.com", "role": "superadmin"},
        headers=_auth(token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_invite_ignores_password_in_body(
    async_client: AsyncClient, mock_email_service, db_session
):
    """Even if an old client POSTs password, it must not be set on the user."""
    token, _tenant_id, _ = await _register_admin(async_client)

    resp = await async_client.post(
        "/team/members",
        json={
            "email": "legacy@example.com",
            "role": "agent",
            "password": "HaxxorAttempt1!",  # Extra field — schema ignores it
        },
        headers=_auth(token),
    )
    assert resp.status_code == 201

    invited = (
        await db_session.execute(
            select(User).where(User.email == "legacy@example.com")
        )
    ).scalar_one()
    assert invited.password_hash is None


# ---------------------------------------------------------------------------
# GET /auth/invite/{token} — public invite lookup
# ---------------------------------------------------------------------------


async def _invite_and_capture_token(
    async_client: AsyncClient, mock_email_service, email: str | None = None
) -> tuple[str, str]:
    """Helper: invite a user and return (raw_token, invitee_email).

    Uses a unique email per call so tests don't collide on DB state.
    """
    if email is None:
        email = f"invitee-{uuid.uuid4()}@example.com"
    owner_token, _tenant_id, _ = await _register_admin(async_client)
    resp = await async_client.post(
        "/team/members",
        json={"email": email, "name": "Invitee", "role": "agent"},
        headers=_auth(owner_token),
    )
    assert resp.status_code == 201, resp.text

    # The raw token is the `?token=...` parameter passed to accept_url
    kwargs = mock_email_service.send_notification.call_args.kwargs
    accept_url = kwargs["accept_url"]
    return accept_url.split("token=", 1)[1], email


@pytest.mark.asyncio
async def test_get_invite_info_returns_details(
    async_client: AsyncClient, mock_email_service
):
    raw_token, invitee_email = await _invite_and_capture_token(async_client, mock_email_service)

    resp = await async_client.get(f"/auth/invite/{raw_token}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == invitee_email
    assert body["tenant_name"] == "OwnerCo"
    assert body["inviter_name"] == "Owner"


@pytest.mark.asyncio
async def test_get_invite_info_returns_404_for_invalid_token(
    async_client: AsyncClient,
):
    resp = await async_client.get("/auth/invite/not-a-real-token")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_invite_info_returns_410_for_expired_token(
    async_client: AsyncClient, mock_email_service, db_session
):
    raw_token, invitee_email = await _invite_and_capture_token(async_client, mock_email_service)

    # Backdate the expiry
    invited = (
        await db_session.execute(
            select(User).where(User.email == invitee_email)
        )
    ).scalar_one()
    invited.invite_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.commit()

    resp = await async_client.get(f"/auth/invite/{raw_token}")
    assert resp.status_code == 410


# ---------------------------------------------------------------------------
# POST /auth/accept-invite — setting password and logging in
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_accept_invite_sets_password_and_clears_token(
    async_client: AsyncClient, mock_email_service, db_session
):
    raw_token, invitee_email = await _invite_and_capture_token(async_client, mock_email_service)

    resp = await async_client.post(
        "/auth/accept-invite",
        json={"token": raw_token, "password": "NewUserPass1!"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body

    # DB state: password set, token cleared
    accepted = (
        await db_session.execute(
            select(User).where(User.email == invitee_email)
        )
    ).scalar_one()
    assert accepted.password_hash is not None
    assert accepted.invite_token_hash is None
    assert accepted.invite_expires_at is None
    assert accepted.consent_at is not None


@pytest.mark.asyncio
async def test_accept_invite_can_override_name(
    async_client: AsyncClient, mock_email_service, db_session
):
    raw_token, invitee_email = await _invite_and_capture_token(async_client, mock_email_service)

    resp = await async_client.post(
        "/auth/accept-invite",
        json={
            "token": raw_token,
            "password": "NewUserPass1!",
            "name": "Real Name",
        },
    )
    assert resp.status_code == 200

    accepted = (
        await db_session.execute(
            select(User).where(User.email == invitee_email)
        )
    ).scalar_one()
    assert accepted.name == "Real Name"


@pytest.mark.asyncio
async def test_accept_invite_rejected_on_second_use(
    async_client: AsyncClient, mock_email_service
):
    raw_token, _invitee_email = await _invite_and_capture_token(async_client, mock_email_service)

    first = await async_client.post(
        "/auth/accept-invite",
        json={"token": raw_token, "password": "FirstPass1!"},
    )
    assert first.status_code == 200

    # Second attempt with the same token should 404 (token was cleared)
    second = await async_client.post(
        "/auth/accept-invite",
        json={"token": raw_token, "password": "SecondPass1!"},
    )
    assert second.status_code == 404


@pytest.mark.asyncio
async def test_accept_invite_rejected_when_expired(
    async_client: AsyncClient, mock_email_service, db_session
):
    raw_token, invitee_email = await _invite_and_capture_token(async_client, mock_email_service)
    invited = (
        await db_session.execute(
            select(User).where(User.email == invitee_email)
        )
    ).scalar_one()
    invited.invite_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.commit()

    resp = await async_client.post(
        "/auth/accept-invite",
        json={"token": raw_token, "password": "LatePass1!"},
    )
    assert resp.status_code == 410


@pytest.mark.asyncio
async def test_accept_invite_requires_minimum_password_length(
    async_client: AsyncClient, mock_email_service
):
    raw_token, _invitee_email = await _invite_and_capture_token(async_client, mock_email_service)

    resp = await async_client.post(
        "/auth/accept-invite",
        json={"token": raw_token, "password": "short"},
    )
    assert resp.status_code == 422  # Pydantic validation failure


# ---------------------------------------------------------------------------
# Login + listing behaviour with pending invites
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_fails_for_pending_invitee(
    async_client: AsyncClient, mock_email_service
):
    _raw_token, invitee_email = await _invite_and_capture_token(async_client, mock_email_service)

    resp = await async_client.post(
        "/auth/login",
        json={"email": invitee_email, "password": "AnyPassword1!"},
    )
    assert resp.status_code == 401  # Generic invalid credentials


@pytest.mark.asyncio
async def test_login_succeeds_after_accept(
    async_client: AsyncClient, mock_email_service
):
    raw_token, invitee_email = await _invite_and_capture_token(async_client, mock_email_service)

    # Accept the invite
    accept = await async_client.post(
        "/auth/accept-invite",
        json={"token": raw_token, "password": "NewUserPass1!"},
    )
    assert accept.status_code == 200

    # Now log in with the new password
    login = await async_client.post(
        "/auth/login",
        json={"email": invitee_email, "password": "NewUserPass1!"},
    )
    assert login.status_code == 200
    assert "access_token" in login.json()


@pytest.mark.asyncio
async def test_team_list_shows_pending_flag(
    async_client: AsyncClient, mock_email_service
):
    owner_token, _tenant_id, _ = await _register_admin(async_client)

    # Invite someone
    await async_client.post(
        "/team/members",
        json={"email": "pending-list@example.com", "role": "agent"},
        headers=_auth(owner_token),
    )

    resp = await async_client.get("/team/members", headers=_auth(owner_token))
    assert resp.status_code == 200
    members = resp.json()
    by_email = {m["email"]: m for m in members}

    # Invitee shows as pending
    assert by_email["pending-list@example.com"]["pending_invite"] is True
    # Owner (who registered normally) is not pending
    owner_row = next(m for m in members if m["email"].startswith("owner-"))
    assert owner_row["pending_invite"] is False
