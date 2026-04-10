"""Unit tests for the AI consent enforcement helpers and agent-level guard."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from listingjet.agents.base import AgentContext, BaseAgent
from listingjet.services.ai_consent import (
    ConsentRevokedError,
    require_tenant_ai_consent,
    tenant_has_ai_consent,
)


def _mock_session_returning(scalar_value):
    """Build an AsyncSession-like mock that returns scalar_value from a scalar_one_or_none."""
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_value
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_tenant_has_ai_consent_true_when_user_found():
    session = _mock_session_returning(uuid.uuid4())
    assert await tenant_has_ai_consent(session, uuid.uuid4()) is True


@pytest.mark.asyncio
async def test_tenant_has_ai_consent_false_when_no_users():
    session = _mock_session_returning(None)
    assert await tenant_has_ai_consent(session, uuid.uuid4()) is False


@pytest.mark.asyncio
async def test_require_tenant_ai_consent_raises_when_missing():
    session = _mock_session_returning(None)
    with pytest.raises(ConsentRevokedError, match="test_agent"):
        await require_tenant_ai_consent(session, uuid.uuid4(), agent_name="test_agent")


@pytest.mark.asyncio
async def test_require_tenant_ai_consent_passes_when_present():
    session = _mock_session_returning(uuid.uuid4())
    # Should not raise
    await require_tenant_ai_consent(session, uuid.uuid4(), agent_name="test_agent")


@pytest.mark.asyncio
async def test_tenant_has_ai_consent_accepts_string_tenant_id():
    session = _mock_session_returning(uuid.uuid4())
    assert await tenant_has_ai_consent(session, str(uuid.uuid4())) is True


# ---------------------------------------------------------------------------
# BaseAgent.instrumented_execute enforces requires_ai_consent
# ---------------------------------------------------------------------------


class _ConsentRequiredAgent(BaseAgent):
    agent_name = "fake_ai_agent"
    requires_ai_consent = True

    def __init__(self):
        self.executed = False

    async def execute(self, context: AgentContext) -> dict:
        self.executed = True
        return {"ok": True}


class _NoConsentAgent(BaseAgent):
    agent_name = "fake_nonai_agent"
    # requires_ai_consent defaults to False

    def __init__(self):
        self.executed = False

    async def execute(self, context: AgentContext) -> dict:
        self.executed = True
        return {"ok": True}


@pytest.mark.asyncio
async def test_instrumented_execute_blocks_ai_agent_when_consent_revoked():
    agent = _ConsentRequiredAgent()
    ctx = AgentContext(listing_id=str(uuid.uuid4()), tenant_id=str(uuid.uuid4()))

    with patch(
        "listingjet.services.ai_consent.tenant_has_ai_consent",
        new=AsyncMock(return_value=False),
    ), patch(
        "listingjet.database.AsyncSessionLocal"
    ) as session_factory:
        session_ctx = MagicMock()
        session_ctx.__aenter__ = AsyncMock(return_value=MagicMock())
        session_ctx.__aexit__ = AsyncMock(return_value=None)
        session_factory.return_value = session_ctx

        with pytest.raises(ConsentRevokedError):
            await agent.instrumented_execute(ctx)

    assert agent.executed is False


@pytest.mark.asyncio
async def test_instrumented_execute_allows_ai_agent_with_consent():
    agent = _ConsentRequiredAgent()
    ctx = AgentContext(listing_id=str(uuid.uuid4()), tenant_id=str(uuid.uuid4()))

    with patch(
        "listingjet.services.ai_consent.tenant_has_ai_consent",
        new=AsyncMock(return_value=True),
    ), patch(
        "listingjet.database.AsyncSessionLocal"
    ) as session_factory:
        session_ctx = MagicMock()
        session_ctx.__aenter__ = AsyncMock(return_value=MagicMock())
        session_ctx.__aexit__ = AsyncMock(return_value=None)
        session_factory.return_value = session_ctx

        result = await agent.instrumented_execute(ctx)

    assert agent.executed is True
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_instrumented_execute_skips_consent_check_for_non_ai_agent():
    agent = _NoConsentAgent()
    ctx = AgentContext(listing_id=str(uuid.uuid4()), tenant_id=str(uuid.uuid4()))

    # Even with no consent in the tenant, a non-AI agent must run.
    with patch(
        "listingjet.services.ai_consent.tenant_has_ai_consent",
        new=AsyncMock(return_value=False),
    ):
        result = await agent.instrumented_execute(ctx)

    assert agent.executed is True
    assert result == {"ok": True}
