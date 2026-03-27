# tests/test_agents/test_pipeline.py
"""
End-to-end smoke test: run all agents in sequence with mock providers.
Verifies state machine progression and that each agent produces correct DB output.
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from launchlens.agents.ingestion import IngestionAgent
from launchlens.agents.vision import VisionAgent
from launchlens.agents.coverage import CoverageAgent
from launchlens.agents.packaging import PackagingAgent
from launchlens.agents.content import ContentAgent
from launchlens.agents.brand import BrandAgent
from launchlens.agents.distribution import DistributionAgent
from launchlens.agents.base import AgentContext
from launchlens.models.listing import Listing, ListingState
from launchlens.models.vision_result import VisionResult
from launchlens.models.package_selection import PackageSelection
from launchlens.providers.base import VisionLabel
from sqlalchemy import select
from tests.test_agents.conftest import make_session_factory


@pytest.fixture
async def pipeline_listing(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "456 Oak Ave", "city": "Dallas", "state": "TX"},
        metadata_={"beds": 4, "baths": 3, "sqft": 2400, "price": 450000},
        state=ListingState.UPLOADING,
    )
    db_session.add(listing)
    await db_session.flush()
    return listing


@pytest.fixture
async def pipeline_assets(db_session, pipeline_listing):
    from launchlens.models.asset import Asset
    assets = []
    shot_hashes = [("aaa", "exterior"), ("bbb", "living_room"), ("ccc", "kitchen"),
                   ("ddd", "bedroom"), ("eee", "bathroom")]
    for h, _ in shot_hashes:
        a = Asset(
            tenant_id=pipeline_listing.tenant_id,
            listing_id=pipeline_listing.id,
            file_path=f"listings/{pipeline_listing.id}/{h}.jpg",
            file_hash=h,
            state="uploaded",
        )
        db_session.add(a)
        assets.append(a)
    await db_session.flush()
    return assets, shot_hashes


@pytest.mark.asyncio
async def test_full_pipeline(db_session, pipeline_listing, pipeline_assets):
    assets, shot_hashes = pipeline_assets
    listing = pipeline_listing
    sf = make_session_factory(db_session)
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    # Map shot type keys to label names recognized by VisionAgent's ROOM_LABEL_MAP.
    # The fallback .replace("_", " ") works for most room labels, but new shot types
    # should be explicitly added here if they don't match ROOM_LABEL_MAP keys exactly.
    SHOT_TO_LABEL_NAME = {
        "exterior": "building exterior",
        "living_room": "living room",
        "kitchen": "kitchen",
        "bedroom": "bedroom",
        "bathroom": "bathroom",
    }

    # Build lookup: file_hash -> shot_type labels
    hash_to_room_label = {h: shot_type for h, shot_type in shot_hashes}

    async def mock_analyze(image_url):
        # image_url is like "listings/{listing_id}/aaa.jpg"
        file_hash = image_url.split("/")[-1].split(".")[0]
        shot_type = hash_to_room_label.get(file_hash, "living_room")
        label_name = SHOT_TO_LABEL_NAME.get(shot_type, shot_type.replace("_", " "))
        return [
            VisionLabel(name=label_name, confidence=0.95, category="room"),
            VisionLabel(name="natural light", confidence=0.88, category="quality"),
            VisionLabel(name="hardwood", confidence=0.82, category="feature"),
        ]

    mock_vision = MagicMock()
    mock_vision.analyze = mock_analyze

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="Stunning 4BR/3BA home with modern finishes.")

    mock_template = MagicMock()
    mock_template.render = AsyncMock(return_value=b"%PDF-content")

    mock_storage = MagicMock()
    mock_storage.upload = MagicMock(return_value=f"listings/{listing.id}/flyer.pdf")

    # Step 1: Ingestion
    r = await IngestionAgent(session_factory=sf).execute(ctx)
    assert r["ingested_count"] == 5
    await db_session.refresh(listing)
    assert listing.state == ListingState.ANALYZING

    # Step 2: Vision (Tier 1 only for smoke test)
    r = await VisionAgent(vision_provider=mock_vision, session_factory=sf).run_tier1(ctx)
    assert r == 5
    vrs = (await db_session.execute(select(VisionResult))).scalars().all()
    assert len(vrs) == 5

    # Step 3: Coverage — all 5 shot types present, no gaps
    r = await CoverageAgent(session_factory=sf).execute(ctx)
    assert r["missing_shots"] == []

    # Step 4: Packaging
    r = await PackagingAgent(session_factory=sf).execute(ctx)
    assert r["total_selected"] == 5
    await db_session.refresh(listing)
    assert listing.state == ListingState.AWAITING_REVIEW

    # Step 5: Content
    r = await ContentAgent(llm_provider=mock_llm, session_factory=sf).execute(ctx)
    assert r["fha_passed"] is True
    assert len(r["copy"]) > 0

    # Step 6: Brand
    r = await BrandAgent(template_provider=mock_template, storage_service=mock_storage, session_factory=sf).execute(ctx)
    assert "flyer_s3_key" in r

    # Step 7: Manually set to APPROVED (simulates human review)
    listing.state = ListingState.APPROVED
    await db_session.flush()

    # Step 8: Distribution
    r = await DistributionAgent(session_factory=sf).execute(ctx)
    assert r["status"] == "delivered"
    await db_session.refresh(listing)
    assert listing.state == ListingState.DELIVERED
