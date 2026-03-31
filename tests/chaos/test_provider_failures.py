"""
Chaos engineering tests — verify agents handle provider failures gracefully.

These tests inject faults (DB commit failures, vision/LLM provider errors)
and assert that each agent either raises cleanly or degrades gracefully
according to its design contract.
"""
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from listingjet.agents.base import AgentContext
from listingjet.agents.content import ContentAgent
from listingjet.agents.ingestion import IngestionAgent
from listingjet.agents.photo_compliance import PhotoComplianceAgent

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
    not swallow the error — it should propagate so Temporal can retry."""

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
# 2. PhotoComplianceAgent — vision provider failure -> graceful degradation
# ---------------------------------------------------------------------------

class TestPhotoComplianceVisionFailure:
    """PhotoComplianceAgent catches vision errors and treats photos as
    compliant so that export is never blocked by an infrastructure outage."""

    @pytest.mark.asyncio
    async def test_vision_failure_returns_all_compliant(self):
        """When the vision provider raises on every call the agent should
        return all_compliant=True (graceful degradation)."""
        failing_vision = AsyncMock()
        failing_vision.analyze_with_prompt.side_effect = RuntimeError(
            "OpenAI API 500 Internal Server Error"
        )

        mock_storage = MagicMock()
        mock_storage.presigned_url.return_value = "https://s3.example.com/photo.jpg"

        listing_id = uuid.uuid4()

        mock_asset_a = MagicMock()
        mock_asset_a.id = uuid.uuid4()
        mock_asset_a.file_path = "s3://bucket/photo_0.jpg"

        mock_asset_b = MagicMock()
        mock_asset_b.id = uuid.uuid4()
        mock_asset_b.file_path = "s3://bucket/photo_1.jpg"

        query_result = MagicMock()
        query_result.all.return_value = [
            (MagicMock(), mock_asset_a),
            (MagicMock(), mock_asset_b),
        ]

        session = _make_mock_session()
        session.get.return_value = MagicMock(id=listing_id)
        session.execute.return_value = query_result

        factory = _make_session_factory(session)
        ctx = AgentContext(listing_id=str(listing_id), tenant_id=str(uuid.uuid4()))

        agent = PhotoComplianceAgent(
            vision_provider=failing_vision,
            storage_service=mock_storage,
            session_factory=factory,
        )
        with patch("listingjet.agents.photo_compliance.emit_event", new_callable=AsyncMock):
            result = await agent.execute(ctx)

        assert result["all_compliant"] is True
        assert result["flagged_count"] == 0
        assert result["total_photos"] == 2
        assert failing_vision.analyze_with_prompt.call_count == 2

    @pytest.mark.asyncio
    async def test_vision_timeout_returns_compliant(self):
        """A timeout from the vision provider is treated as compliant."""
        failing_vision = AsyncMock()
        failing_vision.analyze_with_prompt.side_effect = TimeoutError(
            "Request timed out after 30s"
        )

        mock_storage = MagicMock()
        mock_storage.presigned_url.return_value = "https://s3.example.com/photo.jpg"

        listing_id = uuid.uuid4()
        mock_asset = MagicMock()
        mock_asset.id = uuid.uuid4()
        mock_asset.file_path = "s3://bucket/photo_0.jpg"

        query_result = MagicMock()
        query_result.all.return_value = [(MagicMock(), mock_asset)]

        session = _make_mock_session()
        session.get.return_value = MagicMock(id=listing_id)
        session.execute.return_value = query_result

        factory = _make_session_factory(session)
        ctx = AgentContext(listing_id=str(listing_id), tenant_id=str(uuid.uuid4()))

        agent = PhotoComplianceAgent(
            vision_provider=failing_vision,
            storage_service=mock_storage,
            session_factory=factory,
        )
        with patch("listingjet.agents.photo_compliance.emit_event", new_callable=AsyncMock):
            result = await agent.execute(ctx)

        assert result["all_compliant"] is True
        assert result["compliant_count"] == 1


# ---------------------------------------------------------------------------
# 3. ContentAgent — LLM provider failure should raise cleanly
# ---------------------------------------------------------------------------

class TestContentAgentLLMFailure:
    """ContentAgent does NOT gracefully degrade — an LLM failure must raise
    so Temporal retries the activity."""

    @pytest.mark.asyncio
    async def test_llm_provider_error_propagates(self):
        """If the LLM provider raises, ContentAgent must not swallow it."""
        failing_llm = AsyncMock()
        failing_llm.complete.side_effect = RuntimeError(
            "OpenAI API rate limit exceeded"
        )

        listing_id = uuid.uuid4()
        mock_listing = MagicMock()
        mock_listing.id = listing_id
        mock_listing.metadata_ = {"beds": 3, "baths": 2, "sqft": 1800}

        vr_result = MagicMock()
        vr_result.scalars.return_value.all.return_value = []

        session = _make_mock_session()
        session.get.return_value = mock_listing
        session.execute.return_value = vr_result

        factory = _make_session_factory(session)
        ctx = AgentContext(listing_id=str(listing_id), tenant_id=str(uuid.uuid4()))

        agent = ContentAgent(llm_provider=failing_llm, session_factory=factory)

        with pytest.raises(RuntimeError, match="rate limit exceeded"):
            await agent.execute(ctx)

    @pytest.mark.asyncio
    async def test_llm_returns_invalid_json_raises(self):
        """If the LLM returns garbage instead of JSON, the agent must raise."""
        broken_llm = AsyncMock()
        broken_llm.complete.return_value = "this is not json at all"

        listing_id = uuid.uuid4()
        mock_listing = MagicMock()
        mock_listing.id = listing_id
        mock_listing.metadata_ = {"beds": 3, "baths": 2}

        vr_result = MagicMock()
        vr_result.scalars.return_value.all.return_value = []

        session = _make_mock_session()
        session.get.return_value = mock_listing
        session.execute.return_value = vr_result

        factory = _make_session_factory(session)
        ctx = AgentContext(listing_id=str(listing_id), tenant_id=str(uuid.uuid4()))

        agent = ContentAgent(llm_provider=broken_llm, session_factory=factory)

        with pytest.raises(Exception):
            await agent.execute(ctx)

    @pytest.mark.asyncio
    async def test_llm_connection_error_propagates(self):
        """A network-level connection error should propagate cleanly."""
        failing_llm = AsyncMock()
        failing_llm.complete.side_effect = ConnectionError(
            "Failed to connect to api.openai.com"
        )

        listing_id = uuid.uuid4()
        mock_listing = MagicMock()
        mock_listing.id = listing_id
        mock_listing.metadata_ = {"beds": 2, "baths": 1}

        vr_result = MagicMock()
        vr_result.scalars.return_value.all.return_value = []

        session = _make_mock_session()
        session.get.return_value = mock_listing
        session.execute.return_value = vr_result

        factory = _make_session_factory(session)
        ctx = AgentContext(listing_id=str(listing_id), tenant_id=str(uuid.uuid4()))

        agent = ContentAgent(llm_provider=failing_llm, session_factory=factory)

        with pytest.raises(ConnectionError, match="Failed to connect"):
            await agent.execute(ctx)
