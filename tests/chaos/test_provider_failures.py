"""
Chaos engineering tests — verify agents handle provider failures gracefully.

These tests inject faults (DB commit failures, vision/LLM provider errors)
and assert that each agent either raises cleanly or degrades gracefully
according to its design contract.
"""
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from listingjet.agents.base import AgentContext
from listingjet.agents.content_social import ContentSocialAgent
from listingjet.agents.ingestion import IngestionAgent
from listingjet.providers.claude import ProviderOutputError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_context() -> AgentContext:
    return AgentContext(
        listing_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
    )


def _make_session_factory(session):
    """Mirror of tests/test_agents/conftest.py helper."""
    @asynccontextmanager
    async def factory():
        yield session
    return factory


def _noop_nested_ctx():
    """Return an async context manager that does nothing (simulates begin_nested)."""
    @asynccontextmanager
    async def _ctx():
        yield
    return _ctx()


def _make_mock_session(**overrides):
    """Build a MagicMock session that works with the agent transaction pattern.

    The agents do::

        async with (session.begin() if not session.in_transaction() else session.begin_nested()):

    ``begin_nested()`` must be a *regular* callable that returns an async
    context manager (not a coroutine).  ``AsyncMock`` would make it a
    coroutine, which breaks the ``async with`` protocol.  So we use
    ``MagicMock`` for the session shell and attach ``AsyncMock`` only for
    truly awaitable methods (``execute``, ``get``, ``flush``, ``commit``).
    """
    session = MagicMock()
    session.in_transaction.return_value = True
    session.begin_nested = _noop_nested_ctx  # callable -> async-ctx-manager

    # Awaitable methods
    session.execute = AsyncMock()
    session.get = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    for key, value in overrides.items():
        setattr(session, key, value)
    return session


# ---------------------------------------------------------------------------
# 1. IngestionAgent — DB failure on commit should propagate as an exception
# ---------------------------------------------------------------------------

class TestIngestionAgentDBFailure:
    """When the database raises during the transaction, IngestionAgent must
    not swallow the error — it should propagate so the job runner can retry."""

    @pytest.mark.asyncio
    async def test_commit_failure_propagates(self):
        """Simulate a DB error inside begin_nested() and verify it raises."""
        session = MagicMock()
        session.in_transaction.return_value = True

        @asynccontextmanager
        async def _exploding_nested():
            raise RuntimeError("simulated DB failure")
            yield  # noqa: unreachable

        session.begin_nested = _exploding_nested

        factory = _make_session_factory(session)
        agent = IngestionAgent(session_factory=factory)

        with pytest.raises(RuntimeError, match="simulated DB failure"):
            await agent.execute(_make_context())

    @pytest.mark.asyncio
    async def test_execute_failure_on_query(self):
        """If session.execute raises (e.g. connection dropped), error propagates."""
        session = _make_mock_session()
        session.execute.side_effect = ConnectionError("connection reset by peer")

        factory = _make_session_factory(session)
        agent = IngestionAgent(session_factory=factory)

        with pytest.raises(ConnectionError, match="connection reset"):
            await agent.execute(_make_context())


# ---------------------------------------------------------------------------
# 2. Photo analysis — vision failure is NO LONGER graceful
# ---------------------------------------------------------------------------
# The compliance sweep is now part of PhotoAnalysisAgent, which deliberately
# raises when more than half the photos fail instead of degrading to
# "all compliant". That behaviour is covered against a real database in
# tests/test_agents/test_photo_analysis.py.

# ---------------------------------------------------------------------------
# 3. ContentSocialAgent — Claude failure should raise cleanly
# ---------------------------------------------------------------------------

class TestContentSocialAgentLLMFailure:
    """ContentSocialAgent does NOT gracefully degrade — a Claude failure must
    raise so the job runner retries the step, and no SocialContent rows or
    completion event should be written."""

    @pytest.mark.asyncio
    async def test_claude_provider_error_propagates(self, db_session):
        """If Claude raises, ContentSocialAgent must not swallow it."""
        from sqlalchemy import select

        from listingjet.models.listing import Listing, ListingState
        from listingjet.models.outbox import Outbox
        from listingjet.models.social_content import SocialContent

        listing = Listing(
            tenant_id=uuid.uuid4(), address={"street": "1 Chaos St"},
            metadata_={"beds": 3, "baths": 2, "sqft": 1800},
            state=ListingState.AWAITING_REVIEW,
        )
        db_session.add(listing)
        await db_session.flush()

        failing_claude = AsyncMock()
        failing_claude.complete_json.side_effect = RuntimeError(
            "Claude API rate limit exceeded"
        )

        factory = _make_session_factory(db_session)
        ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
        agent = ContentSocialAgent(claude=failing_claude, session_factory=factory)

        with pytest.raises(RuntimeError, match="rate limit exceeded"):
            await agent.execute(ctx)

        rows = (await db_session.execute(
            select(SocialContent).where(SocialContent.listing_id == listing.id)
        )).scalars().all()
        assert rows == []
        evt = (await db_session.execute(
            select(Outbox).where(Outbox.event_type == "content_social.completed")
        )).scalars().first()
        assert evt is None

    @pytest.mark.asyncio
    async def test_claude_connection_error_propagates(self, db_session):
        """A network-level connection error should propagate cleanly."""
        from sqlalchemy import select

        from listingjet.models.listing import Listing, ListingState
        from listingjet.models.outbox import Outbox
        from listingjet.models.social_content import SocialContent

        listing = Listing(
            tenant_id=uuid.uuid4(), address={"street": "2 Chaos St"},
            metadata_={"beds": 2, "baths": 1},
            state=ListingState.AWAITING_REVIEW,
        )
        db_session.add(listing)
        await db_session.flush()

        failing_claude = AsyncMock()
        failing_claude.complete_json.side_effect = ConnectionError(
            "Failed to connect to api.anthropic.com"
        )

        factory = _make_session_factory(db_session)
        ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
        agent = ContentSocialAgent(claude=failing_claude, session_factory=factory)

        with pytest.raises(ConnectionError, match="Failed to connect"):
            await agent.execute(ctx)

        rows = (await db_session.execute(
            select(SocialContent).where(SocialContent.listing_id == listing.id)
        )).scalars().all()
        assert rows == []
        evt = (await db_session.execute(
            select(Outbox).where(Outbox.event_type == "content_social.completed")
        )).scalars().first()
        assert evt is None

    @pytest.mark.asyncio
    async def test_claude_provider_output_error_propagates(self, db_session):
        """A refused/unstructured Claude response should propagate cleanly."""
        from sqlalchemy import select

        from listingjet.models.listing import Listing, ListingState
        from listingjet.models.outbox import Outbox
        from listingjet.models.social_content import SocialContent

        listing = Listing(
            tenant_id=uuid.uuid4(), address={"street": "3 Chaos St"},
            metadata_={"beds": 4, "baths": 3},
            state=ListingState.AWAITING_REVIEW,
        )
        db_session.add(listing)
        await db_session.flush()

        failing_claude = AsyncMock()
        failing_claude.complete_json.side_effect = ProviderOutputError("refused")

        factory = _make_session_factory(db_session)
        ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
        agent = ContentSocialAgent(claude=failing_claude, session_factory=factory)

        with pytest.raises(ProviderOutputError, match="refused"):
            await agent.execute(ctx)

        rows = (await db_session.execute(
            select(SocialContent).where(SocialContent.listing_id == listing.id)
        )).scalars().all()
        assert rows == []
        evt = (await db_session.execute(
            select(Outbox).where(Outbox.event_type == "content_social.completed")
        )).scalars().first()
        assert evt is None
