from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from listingjet.agents.base import AgentContext
from listingjet.agents.brand import BrandAgent
from listingjet.models.package_selection import PackageSelection
from tests.test_agents.conftest import make_session_factory


@pytest.fixture
async def hero_selection(db_session, listing, assets):
    ps = PackageSelection(
        tenant_id=listing.tenant_id,
        listing_id=listing.id,
        asset_id=assets[0].id,
        channel="mls",
        position=0,
        selected_by="ai",
        composite_score=0.92,
    )
    db_session.add(ps)
    await db_session.flush()
    return ps


@pytest.mark.asyncio
@patch("listingjet.agents.brand.settings")
async def test_brand_renders_and_uploads_flyer(mock_settings, db_session, listing, assets, hero_selection):
    mock_settings.canva_default_template_id = "DAGtest123"

    mock_template = MagicMock()
    mock_template.render = AsyncMock(return_value=b"%PDF-flyer-content")

    mock_storage = MagicMock()
    mock_storage.upload = MagicMock(return_value=f"listings/{listing.id}/flyer.pdf")

    agent = BrandAgent(
        template_provider=mock_template,
        storage_service=mock_storage,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert mock_template.render.called
    assert mock_storage.upload.called
    assert "flyer_s3_key" in result
    assert str(listing.id) in result["flyer_s3_key"]


@pytest.mark.asyncio
@patch("listingjet.agents.brand.settings")
async def test_brand_emits_event(mock_settings, db_session, listing, assets, hero_selection):
    from sqlalchemy import select

    from listingjet.models.outbox import Outbox

    mock_settings.canva_default_template_id = "DAGtest123"

    mock_template = MagicMock()
    mock_template.render = AsyncMock(return_value=b"%PDF-content")
    mock_storage = MagicMock()
    mock_storage.upload = MagicMock(return_value="listings/test/flyer.pdf")

    agent = BrandAgent(
        template_provider=mock_template,
        storage_service=mock_storage,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.execute(ctx)
    await db_session.flush()

    rows = (await db_session.execute(
        select(Outbox).where(Outbox.event_type == "brand.completed")
    )).scalars().all()
    assert len(rows) == 1
