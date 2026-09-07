import uuid

import pytest
from sqlalchemy import select

from listingjet.models.vision_result import VisionResult


def test_vision_result_analysis_columns_exist():
    """Assert the five new analysis columns exist in the VisionResult table."""
    columns = {col.name for col in VisionResult.__table__.columns}
    assert "hero_score" in columns
    assert "is_photo" in columns
    assert "is_empty_room" in columns
    assert "features" in columns
    assert "compliance" in columns


@pytest.mark.asyncio
async def test_vision_result_analysis_data_roundtrip(db_session):
    """Test that VisionResult with analysis data round-trips through db_session."""
    asset_id = uuid.uuid4()
    vr = VisionResult(
        asset_id=asset_id,
        tier=1,
        compliance={"people": True},
        features=["pool"],
        is_empty_room=False,
        is_photo=True,
        hero_score=71,
    )
    db_session.add(vr)
    await db_session.flush()

    row = (await db_session.execute(select(VisionResult).where(VisionResult.id == vr.id))).scalar_one()
    assert row.asset_id == asset_id
    assert row.tier == 1
    assert row.compliance == {"people": True}
    assert row.features == ["pool"]
    assert row.is_empty_room is False
    assert row.is_photo is True
    assert row.hero_score == 71
