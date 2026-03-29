import io
import json
import uuid
import zipfile
from unittest.mock import MagicMock

import pytest

from listingjet.agents.base import AgentContext
from listingjet.agents.mls_export import MLSExportAgent
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing, ListingState
from listingjet.models.outbox import Outbox
from listingjet.models.package_selection import PackageSelection
from listingjet.models.social_content import SocialContent
from listingjet.models.vision_result import VisionResult

from .conftest import make_session_factory

# Minimal valid JPEG bytes (1x1 pixel)
_TINY_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
    b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
    b"\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04"
    b"\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"
    b"\x22q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16"
    b"\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz"
    b"\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99"
    b"\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7"
    b"\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5"
    b"\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1"
    b"\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa"
    b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00T\xdb\xae\x8a(\x03\xff\xd9"
)

_FLYER_BYTES = b"%PDF-1.4 fake flyer content"

ROOM_LABELS = ["exterior_front", "kitchen", "living_room"]


async def _setup_approved_listing(db_session, include_social=False):
    """Create APPROVED listing with 3 packaged photos, vision results, optionally social content."""
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "100 Export Ave", "city": "Denver", "state": "CO"},
        metadata_={"beds": 4, "baths": 3, "sqft": 2400},
        state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    assets = []
    for i in range(3):
        a = Asset(
            listing_id=listing.id,
            tenant_id=tenant_id,
            file_path=f"listings/{listing.id}/photos/photo_{i}.jpg",
            file_hash=f"hash{i:03d}",
            state="uploaded",
        )
        db_session.add(a)
        assets.append(a)
    await db_session.flush()

    for i, a in enumerate(assets):
        pkg = PackageSelection(
            tenant_id=tenant_id,
            listing_id=listing.id,
            asset_id=a.id,
            channel="mls",
            position=i,
            selected_by="ai",
            composite_score=0.9 - i * 0.1,
        )
        db_session.add(pkg)

        vr = VisionResult(
            asset_id=a.id,
            tier=1,
            room_label=ROOM_LABELS[i],
            is_interior=(i > 0),
            quality_score=90 - i * 5,
            commercial_score=85,
            hero_candidate=(i == 0),
            hero_explanation=f"Caption for {ROOM_LABELS[i]}",
            raw_labels={},
            model_used="test-model",
        )
        db_session.add(vr)
    await db_session.flush()

    if include_social:
        for platform in ["instagram", "facebook"]:
            sc = SocialContent(
                tenant_id=tenant_id,
                listing_id=listing.id,
                platform=platform,
                caption=f"Check out this listing on {platform}!",
                hashtags=["realestate", "newlisting"],
                cta="Schedule a tour today",
            )
            db_session.add(sc)
        await db_session.flush()

    return listing, tenant_id


def _make_storage_service():
    storage = MagicMock()
    storage.uploaded = {}

    def fake_upload(key, data, content_type):
        if isinstance(data, (bytes, bytearray)):
            storage.uploaded[key] = data
        elif hasattr(data, "read"):
            storage.uploaded[key] = data.read()
        else:
            storage.uploaded[key] = data
        return key

    storage.upload = MagicMock(side_effect=fake_upload)
    storage.presigned_url = MagicMock(return_value="https://s3.example.com/presigned")

    def fake_download(key):
        if "flyer" in key:
            return _FLYER_BYTES
        return _TINY_JPEG

    storage.download = MagicMock(side_effect=fake_download)
    return storage


@pytest.mark.asyncio
async def test_mls_export_creates_two_bundles(db_session):
    listing, tenant_id = await _setup_approved_listing(db_session, include_social=True)
    storage = _make_storage_service()

    agent = MLSExportAgent(
        storage_service=storage,
        session_factory=make_session_factory(db_session),
        content_result={"mls_safe": "A spacious home.", "marketing": "Stunning retreat."},
        flyer_s3_key=f"listings/{listing.id}/flyer.pdf",
    )

    result = await agent.execute(
        AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id))
    )

    assert "mls_bundle_path" in result
    assert "marketing_bundle_path" in result
    assert result["mls_bundle_path"].endswith("_mls.zip")
    assert result["marketing_bundle_path"].endswith("_marketing.zip")
    # Verify listing was updated
    await db_session.refresh(listing)
    assert listing.mls_bundle_path is not None
    assert listing.marketing_bundle_path is not None


@pytest.mark.asyncio
async def test_mls_bundle_contains_expected_files(db_session):
    listing, tenant_id = await _setup_approved_listing(db_session, include_social=False)
    storage = _make_storage_service()

    agent = MLSExportAgent(
        storage_service=storage,
        session_factory=make_session_factory(db_session),
        content_result={"mls_safe": "A spacious home.", "marketing": "Stunning retreat."},
        flyer_s3_key=f"listings/{listing.id}/flyer.pdf",
    )

    result = await agent.execute(
        AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id))
    )

    # Get the MLS ZIP from uploaded storage
    mls_zip_bytes = storage.uploaded[result["mls_bundle_path"]]
    with zipfile.ZipFile(io.BytesIO(mls_zip_bytes)) as zf:
        names = zf.namelist()
        assert "metadata.csv" in names
        assert "description_mls.txt" in names
        assert "manifest.json" in names

        jpg_files = [n for n in names if n.endswith(".jpg")]
        assert len(jpg_files) == 3
        assert any(n.startswith("00_") for n in jpg_files)

        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["mode"] == "mls"


@pytest.mark.asyncio
async def test_mls_export_emits_event(db_session):
    listing, tenant_id = await _setup_approved_listing(db_session, include_social=False)
    storage = _make_storage_service()

    agent = MLSExportAgent(
        storage_service=storage,
        session_factory=make_session_factory(db_session),
        content_result={"mls_safe": "A spacious home.", "marketing": "Stunning retreat."},
        flyer_s3_key=f"listings/{listing.id}/flyer.pdf",
    )

    await agent.execute(
        AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id))
    )

    from sqlalchemy import select

    result = await db_session.execute(
        select(Outbox).where(Outbox.event_type == "mls_export.completed")
    )
    outbox_row = result.scalar_one_or_none()
    assert outbox_row is not None
    assert outbox_row.listing_id == listing.id


@pytest.mark.asyncio
async def test_mls_export_sets_listing_paths(db_session):
    listing, tenant_id = await _setup_approved_listing(db_session, include_social=False)
    storage = _make_storage_service()

    agent = MLSExportAgent(
        storage_service=storage,
        session_factory=make_session_factory(db_session),
        content_result={"mls_safe": "A spacious home.", "marketing": "Stunning retreat."},
        flyer_s3_key=f"listings/{listing.id}/flyer.pdf",
    )

    await agent.execute(
        AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id))
    )

    await db_session.refresh(listing)
    assert listing.mls_bundle_path is not None
    assert listing.marketing_bundle_path is not None
    assert "_mls.zip" in listing.mls_bundle_path
    assert "_marketing.zip" in listing.marketing_bundle_path
