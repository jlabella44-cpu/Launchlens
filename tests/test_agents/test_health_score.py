"""Unit tests for the HealthScoreAgent."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from listingjet.agents.base import AgentContext
from listingjet.agents.health_score import HealthScoreAgent


@pytest.mark.asyncio
async def test_health_score_agent_executes():
    """HealthScoreAgent calls HealthScoreService and emits events."""
    tenant_id = str(uuid.uuid4())
    listing_id = str(uuid.uuid4())
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)

    mock_score = MagicMock()
    mock_score.overall_score = 75
    mock_score.media_score = 80
    mock_score.content_score = 70
    mock_score.velocity_score = 85
    mock_score.syndication_score = 50
    mock_score.market_score = 50

    mock_tenant = MagicMock()
    mock_tenant.plan = "pro"

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_tenant)

    mock_factory = MagicMock()

    with (
        patch("listingjet.agents.health_score.hs.calculate", new_callable=AsyncMock, return_value=mock_score),
        patch.object(HealthScoreAgent, "session_scope") as mock_scope,
        patch.object(HealthScoreAgent, "emit", new_callable=AsyncMock) as mock_emit,
    ):
        # Make session_scope yield the mock session
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def fake_scope(context):
            yield mock_session, uuid.UUID(listing_id), uuid.UUID(tenant_id)

        mock_scope.side_effect = fake_scope

        agent = HealthScoreAgent(session_factory=mock_factory)
        result = await agent.execute(ctx)

    assert result["overall_score"] == 75
    assert result["media_score"] == 80
    assert mock_emit.call_count >= 1  # At least health.score.updated emitted


@pytest.mark.asyncio
async def test_health_score_agent_emits_alert_below_threshold():
    """HealthScoreAgent emits health.score.alert when score < 60."""
    tenant_id = str(uuid.uuid4())
    listing_id = str(uuid.uuid4())
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)

    mock_score = MagicMock()
    mock_score.overall_score = 45
    mock_score.media_score = 40
    mock_score.content_score = 30
    mock_score.velocity_score = 50
    mock_score.syndication_score = 50
    mock_score.market_score = 50

    mock_tenant = MagicMock()
    mock_tenant.plan = "starter"

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_tenant)

    with (
        patch("listingjet.agents.health_score.hs.calculate", new_callable=AsyncMock, return_value=mock_score),
        patch.object(HealthScoreAgent, "session_scope") as mock_scope,
        patch.object(HealthScoreAgent, "emit", new_callable=AsyncMock) as mock_emit,
    ):
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def fake_scope(context):
            yield mock_session, uuid.UUID(listing_id), uuid.UUID(tenant_id)

        mock_scope.side_effect = fake_scope

        agent = HealthScoreAgent()
        result = await agent.execute(ctx)

    assert result["overall_score"] == 45

    # Should have emitted both health.score.updated AND health.score.alert
    event_types = [call.args[2] for call in mock_emit.call_args_list]
    assert "health.score.updated" in event_types
    assert "health.score.alert" in event_types
