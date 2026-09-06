# tests/test_agents/test_pipeline.py
"""
End-to-end smoke test: run all agents in sequence with mock providers.
Verifies state machine progression and that each agent produces correct DB output.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from listingjet.agents.base import AgentContext
from listingjet.agents.brand import BrandAgent
from listingjet.agents.content import ContentAgent
from listingjet.agents.coverage import CoverageAgent
from listingjet.agents.distribution import DistributionAgent
from listingjet.agents.ingestion import IngestionAgent
from listingjet.agents.packaging import PackagingAgent
from listingjet.agents.photo_analysis import (
    Compliance,
    PhotoAnalysis,
    PhotoAnalysisAgent,
    RoomLabel,
)
from listingjet.models.listing import Listing, ListingState
from listingjet.models.vision_result import VisionResult
from listingjet.providers.mock import MockClaudeClient
from tests.test_agents.conftest import make_session_factory


def _mock_storage_service():
    """Create a mock StorageService that handles download, upload, and presigned URLs."""
    storage = MagicMock()
    # Return small fake JPEG bytes for proxy generation
    storage.download.return_value = _tiny_jpeg()
    storage.upload.return_value = "proxies/test.jpg"
    storage.presigned_url.side_effect = lambda key, **kw: f"https://s3.example.com/{key}?signed=1"
    return storage


def _tiny_jpeg() -> bytes:
    """Generate a minimal valid JPEG for PIL to open."""
    import io

    from PIL import Image
    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def patch_storage_everywhere():
    mock = _mock_storage_service()
    with patch("listingjet.agents.ingestion.get_storage", return_value=mock), \
         patch("listingjet.agents.photo_analysis.get_storage", return_value=mock):
        yield mock


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
    from listingjet.models.asset import Asset
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

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value='{"mls_safe": "Spacious 4BR/3BA home with modern finishes.", "marketing": "Stunning 4BR/3BA home with modern finishes and natural light."}')

    mock_template = MagicMock()
    mock_template.render = AsyncMock(return_value=b"%PDF-content")

    mock_storage = MagicMock()
    mock_storage.upload = MagicMock(return_value=f"listings/{listing.id}/flyer.pdf")

    # Step 1: Ingestion
    r = await IngestionAgent(session_factory=sf).execute(ctx)
    assert r["ingested_count"] == 5
    await db_session.refresh(listing)
    assert listing.state == ListingState.ANALYZING

    # Step 2: Photo analysis (one Claude pass per photo). Ingestion has now
    # written proxy_path on each asset, which is the image the agent presigns.
    hash_to_room_label = {h: shot_type for h, shot_type in shot_hashes}

    def _analysis(room: str) -> PhotoAnalysis:
        return PhotoAnalysis(
            room=RoomLabel(room),
            is_interior=room != "exterior",
            is_photo=True,
            quality=90,
            hero_score=85 if room == "exterior" else 75,
            features=["hardwood floors", "natural light"],
            is_empty_room=False,
            compliance=Compliance(people=False, signage=False, branding=False, text_overlay=False),
            notes=f"Clean {room} shot.",
        )

    claude = MockClaudeClient()
    claude.by_url = {
        f"https://s3.example.com/{a.proxy_path or a.file_path}?signed=1":
            _analysis(hash_to_room_label[a.file_hash])
        for a in assets
    }

    r = await PhotoAnalysisAgent(claude=claude, session_factory=sf).execute(ctx)
    assert r == {"analyzed": 5, "failed": 0, "flagged": 0}
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
    assert len(r["mls_safe"]) > 0
    assert len(r["marketing"]) > 0

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
