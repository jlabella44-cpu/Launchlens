# tests/test_api/test_sse.py
"""Tests for the SSE endpoint GET /sse/listings/{id}/events."""
import asyncio
import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient) -> tuple[str, str]:
    import jwt as pyjwt

    from listingjet.config import settings

    email = f"sse-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "SSE Tester", "company_name": "SSE Co",
        "plan_tier": "free",
    })
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]


async def _create_listing(client: AsyncClient, token: str) -> str:
    resp = await client.post("/listings", json={
        "address": {"street": "1 SSE Lane", "city": "Austin", "state": "TX", "zip": "78701"},
        "metadata": {"beds": 3, "baths": 2, "sqft": 1500, "price": 350000},
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_sse_requires_auth(async_client: AsyncClient):
    """Unauthenticated request returns 401 or 403."""
    listing_id = str(uuid.uuid4())
    resp = await async_client.get(
        f"/sse/listings/{listing_id}/events",
        headers={},
        timeout=3.0,
    )
    assert resp.status_code in (401, 403)


@pytest.mark.skip(reason="SSE streaming hangs in CI — no real disconnect detection")
@pytest.mark.asyncio
async def test_sse_returns_event_stream_content_type(async_client: AsyncClient):
    """Authenticated request for existing listing returns text/event-stream."""
    token, _ = await _register(async_client)
    listing_id = await _create_listing(async_client, token)

    async with asyncio.timeout(10):
        async with async_client.stream(
            "GET",
            f"/sse/listings/{listing_id}/events",
            headers={"Authorization": f"Bearer {token}"},
            timeout=3.0,
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_sse_returns_404_for_missing_listing(async_client: AsyncClient):
    """Non-existent listing returns 404."""
    token, _ = await _register(async_client)
    missing_id = str(uuid.uuid4())
    resp = await async_client.get(
        f"/sse/listings/{missing_id}/events",
        headers={"Authorization": f"Bearer {token}"},
        timeout=3.0,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sse_rejects_bad_query_token(async_client: AsyncClient):
    """Route-level check: an invalid ?token= is rejected before streaming starts
    (fails fast, so it doesn't hit the SSE-hangs-in-CI issue above)."""
    listing_id = str(uuid.uuid4())
    resp = await async_client.get(
        f"/sse/listings/{listing_id}/events",
        params={"token": "not-a-real-jwt"},
        timeout=3.0,
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sse_returns_403_for_other_tenant_listing(async_client: AsyncClient):
    """A listing owned by another tenant returns 403."""
    token_a, _ = await _register(async_client)
    token_b, _ = await _register(async_client)
    listing_id = await _create_listing(async_client, token_a)

    resp = await async_client.get(
        f"/sse/listings/{listing_id}/events",
        headers={"Authorization": f"Bearer {token_b}"},
        timeout=3.0,
    )
    assert resp.status_code == 403


# --- get_current_user_or_query_token: unit-level (no streaming, no hang risk) ---


async def _resolve_current_user(async_client, db_session, *, token_param=None, credentials=None):
    from starlette.requests import Request

    from listingjet.api.deps import get_current_user_or_query_token

    request = Request({"type": "http", "headers": [], "query_string": b""})
    return await get_current_user_or_query_token(
        request, token=token_param, credentials=credentials, db=db_session,
    )


@pytest.mark.asyncio
async def test_query_token_dependency_accepts_valid_token(async_client: AsyncClient, db_session):
    """Same validation path as get_current_user, with the query value as the
    last fallback — a bare ?token= must resolve the same user."""
    token, _ = await _register(async_client)
    user = await _resolve_current_user(async_client, db_session, token_param=token)
    assert user is not None


@pytest.mark.asyncio
async def test_query_token_dependency_rejects_bad_token(async_client: AsyncClient, db_session):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await _resolve_current_user(async_client, db_session, token_param="not-a-real-jwt")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_query_token_dependency_prefers_header_over_query(async_client: AsyncClient, db_session):
    """A valid Authorization header must win even when a (bad) query token is present."""
    from fastapi.security import HTTPAuthorizationCredentials

    token, _ = await _register(async_client)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = await _resolve_current_user(
        async_client, db_session, token_param="not-a-real-jwt", credentials=creds,
    )
    assert user is not None


# --- streaming behaviour: retry directive, Last-Event-ID resume, cursor order ---
#
# httpx's ASGITransport buffers the whole response body before returning (it
# awaits the app to completion), so an infinite SSE stream can never be read
# through `async_client.stream` — that is what the skips above were about.
# These tests call the endpoint directly and drive its body iterator, stopping
# the infinite loop the same way the skipped tests tried to: an
# `asyncio.timeout(...)` around the read plus a `break` once enough frames
# have arrived.


@pytest.fixture
def sse_sessions(test_engine, monkeypatch):
    """Point the stream's per-poll session factory at the test engine."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr("listingjet.api.sse._session_factory", lambda: factory())
    return factory


async def _set_tenant(session, tenant_id):
    from sqlalchemy import text

    await session.execute(
        text("SELECT set_config('app.current_tenant', :tid, true)"),
        {"tid": str(tenant_id)},
    )


async def _insert_events(factory, tenant_id, listing_id, rows):
    """Insert events directly (RLS needs an explicit tenant on the session)."""
    from listingjet.models.event import Event

    async with factory() as session:
        await _set_tenant(session, tenant_id)
        for row in rows:
            session.add(Event(tenant_id=uuid.UUID(str(tenant_id)),
                              listing_id=uuid.UUID(str(listing_id)), **row))
        await session.commit()


async def _load_user(session, tenant_id):
    from sqlalchemy import select

    from listingjet.models.user import User

    await _set_tenant(session, tenant_id)
    result = await session.execute(
        select(User).where(User.tenant_id == uuid.UUID(str(tenant_id)))
    )
    return result.scalars().first()


def _fake_request(headers: dict | None = None):
    """Request whose receive() blocks forever, so is_disconnected() stays False."""
    from starlette.requests import Request

    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]

    async def receive():
        await asyncio.Event().wait()

    return Request({"type": "http", "headers": raw, "query_string": b"",
                    "method": "GET", "path": "/"}, receive)


async def _collect_frames(session, tenant_id, listing_id, *, seconds=5.0,
                          stop_after=None, headers=None):
    """Open the SSE stream and read frames until `stop_after` or `seconds`."""
    from listingjet.api import sse

    user = await _load_user(session, tenant_id)
    assert user is not None
    response = await sse.listing_events(
        listing_id=uuid.UUID(str(listing_id)),
        request=_fake_request(headers),
        _rl=None,
        current_user=user,
        db=session,
    )

    frames: list[str] = []
    buf = ""
    iterator = response.body_iterator
    try:
        async with asyncio.timeout(seconds):
            async for chunk in iterator:
                buf += chunk if isinstance(chunk, str) else chunk.decode()
                while "\n\n" in buf:
                    frame, buf = buf.split("\n\n", 1)
                    frames.append(frame)
                if stop_after is not None and len(frames) >= stop_after:
                    break
    except (TimeoutError, asyncio.TimeoutError):
        pass
    finally:
        await iterator.aclose()
    return frames


def _event_frames(frames):
    return [f for f in frames if f.startswith("id:")]


def _frame_ids(frames):
    return [f.splitlines()[0].removeprefix("id: ") for f in _event_frames(frames)]


def _frame_types(frames):
    return [
        line.removeprefix("event: ")
        for f in _event_frames(frames)
        for line in f.splitlines()
        if line.startswith("event: ")
    ]


@pytest.mark.asyncio
async def test_sse_streams_retry_directive(
    async_client: AsyncClient, db_session, sse_sessions,
):
    """The first frame of every stream is the reconnect-backoff directive."""
    token, tenant_id = await _register(async_client)
    listing_id = await _create_listing(async_client, token)

    frames = await _collect_frames(db_session, tenant_id, listing_id,
                                   seconds=8, stop_after=1)

    assert frames == ["retry: 5000"], frames


@pytest.mark.asyncio
async def test_sse_event_frames_carry_an_id(
    async_client: AsyncClient, db_session, sse_sessions,
):
    """Every event frame carries `id:` so the browser can resume from it."""
    from datetime import datetime, timedelta, timezone

    token, tenant_id = await _register(async_client)
    listing_id = await _create_listing(async_client, token)
    event_id = uuid.uuid4()
    await _insert_events(sse_sessions, tenant_id, listing_id, [
        {"id": event_id, "event_type": "ingestion.completed", "payload": {"n": 1},
         "created_at": datetime.now(timezone.utc) - timedelta(minutes=5)},
    ])

    frames = await _collect_frames(db_session, tenant_id, listing_id,
                                   seconds=8, stop_after=2)

    assert _frame_ids(frames) == [str(event_id)]
    assert _frame_types(frames) == ["ingestion.completed"]


@pytest.mark.asyncio
async def test_sse_last_event_id_skips_already_seen_events(
    async_client: AsyncClient, db_session, sse_sessions,
):
    """A reconnect with Last-Event-ID must not replay events at or before it."""
    from datetime import datetime, timedelta, timezone

    token, tenant_id = await _register(async_client)
    listing_id = await _create_listing(async_client, token)
    base = datetime.now(timezone.utc) - timedelta(minutes=5)
    first, second, third = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    await _insert_events(sse_sessions, tenant_id, listing_id, [
        {"id": first, "event_type": "ingestion.completed", "payload": {},
         "created_at": base},
        {"id": second, "event_type": "coverage.completed", "payload": {},
         "created_at": base + timedelta(seconds=1)},
        {"id": third, "event_type": "packaging.completed", "payload": {},
         "created_at": base + timedelta(seconds=2)},
    ])

    frames = await _collect_frames(
        db_session, tenant_id, listing_id, seconds=8, stop_after=2,
        headers={"Last-Event-ID": str(second)},
    )

    assert _frame_ids(frames) == [str(third)]


@pytest.mark.asyncio
async def test_sse_unknown_last_event_id_starts_from_now(
    async_client: AsyncClient, db_session, sse_sessions,
):
    """An id we cannot place means start from now — never replay everything."""
    from datetime import datetime, timedelta, timezone

    token, tenant_id = await _register(async_client)
    listing_id = await _create_listing(async_client, token)
    await _insert_events(sse_sessions, tenant_id, listing_id, [
        {"id": uuid.uuid4(), "event_type": "ingestion.completed", "payload": {},
         "created_at": datetime.now(timezone.utc) - timedelta(minutes=5)},
    ])

    frames = await _collect_frames(
        db_session, tenant_id, listing_id, seconds=4,
        headers={"Last-Event-ID": str(uuid.uuid4())},
    )

    assert frames[0] == "retry: 5000"
    assert _event_frames(frames) == []


@pytest.mark.asyncio
async def test_sse_cursor_is_stable_for_events_sharing_a_timestamp(
    async_client: AsyncClient, db_session, sse_sessions,
):
    """Two events at the same instant: ordered by (created_at, id), each sent once.

    The old cursor compared UUIDs alone, so the higher-UUID row (inserted
    first here) fell back through the cursor and was replayed on every poll.
    """
    from datetime import datetime, timedelta, timezone

    token, tenant_id = await _register(async_client)
    listing_id = await _create_listing(async_client, token)
    stamp = datetime.now(timezone.utc) - timedelta(minutes=5)
    high = uuid.UUID("ffffffff-ffff-4fff-8fff-ffffffffffff")
    low = uuid.UUID("00000000-0000-4000-8000-000000000001")
    # Inserted high-UUID first: insertion order disagrees with UUID order.
    await _insert_events(sse_sessions, tenant_id, listing_id, [
        {"id": high, "event_type": "ingestion.completed", "payload": {},
         "created_at": stamp},
        {"id": low, "event_type": "coverage.completed", "payload": {},
         "created_at": stamp},
    ])

    # Read across more than one poll interval (2s) so a replay would show up.
    frames = await _collect_frames(db_session, tenant_id, listing_id, seconds=6)

    assert _frame_ids(frames) == [str(low), str(high)]
