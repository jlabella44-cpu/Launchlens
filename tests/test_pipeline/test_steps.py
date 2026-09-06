import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select, text

from listingjet.database import admin_session
from listingjet.pipeline.definition import PIPELINE
from listingjet.pipeline.steps import STEP_FUNCTIONS, StepContext


def test_every_runnable_step_has_a_function():
    expected = {s.name for s in PIPELINE if s.gate != "review"}
    assert set(STEP_FUNCTIONS) == expected


@pytest.mark.asyncio
async def test_mls_export_step_passes_content_and_flyer_from_results():
    ctx = StepContext(listing_id=str(uuid.uuid4()), tenant_id=str(uuid.uuid4()), results={
        "content": {"mls_safe": "A", "marketing": "B"},
        "brand": {"flyer_s3_key": "flyers/x.pdf"},
    })
    with patch("listingjet.pipeline.steps.MLSExportAgent") as agent_cls:
        agent_cls.return_value.instrumented_execute = AsyncMock(return_value={"ok": True})
        out = await STEP_FUNCTIONS["mls_export"](ctx)
    assert out == {"ok": True}
    agent_cls.assert_called_once_with(
        content_result={"mls_safe": "A", "marketing": "B"},
        flyer_s3_key="flyers/x.pdf",
        session_factory=admin_session,
    )


@pytest.mark.asyncio
async def test_vision_tier1_uses_run_tier1():
    ctx = StepContext(listing_id=str(uuid.uuid4()), tenant_id=str(uuid.uuid4()), results={})
    with patch("listingjet.pipeline.steps.VisionAgent") as agent_cls:
        agent_cls.return_value.run_tier1 = AsyncMock(return_value=7)
        out = await STEP_FUNCTIONS["vision_tier1"](ctx)
    assert out == {"count": 7}
    agent_cls.assert_called_once_with(session_factory=admin_session)


@pytest.mark.asyncio
async def test_admin_session_sets_is_admin_flag(test_session_factory):
    async with admin_session(session_factory=test_session_factory) as session:
        result = await session.execute(select(text("current_setting('app.is_admin', true)")))
        value = result.scalar_one()
    assert value == "true"
