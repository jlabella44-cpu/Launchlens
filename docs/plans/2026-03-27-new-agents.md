# New Agents (MLS Export + Social Content) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two new pipeline agents — SocialContentAgent (generates platform-specific social media posts) and MLSExportAgent (packages photos + metadata into a downloadable MLS-ready ZIP bundle) — plus a download API endpoint.

**Architecture:** Both agents follow the existing `BaseAgent` pattern with session injection and Outbox events. `SocialContentAgent` uses the LLM provider (Claude) to generate posts for Instagram, Facebook, LinkedIn, and Twitter/X from listing metadata + top photo selections. `MLSExportAgent` creates a ZIP file containing renamed/resized photos + a metadata CSV, uploads it to S3, and stores the download URL. A new `GET /listings/{id}/export` endpoint returns the export URL. Both agents are wired into the Temporal workflow in Phase 2 (post-approval).

**Tech Stack:** SQLAlchemy 2.0 async, Claude (via ClaudeProvider), S3 (via StorageService), zipfile stdlib, pytest-asyncio

---

## File Structure

```
src/launchlens/
  agents/
    social_content.py          CREATE  — SocialContentAgent (generates social posts)
    mls_export.py              CREATE  — MLSExportAgent (ZIP packaging + S3 upload)
  models/
    social_post.py             CREATE  — SocialPost model (listing_id, platform, caption, hashtags)
    export_bundle.py           CREATE  — ExportBundle model (listing_id, s3_key, format, created_at)
  activities/
    pipeline.py                MODIFY  — add run_social_content, run_mls_export activities
  workflows/
    listing_pipeline.py        MODIFY  — wire new agents into Phase 2
  api/
    listings.py                MODIFY  — add GET /listings/{id}/export, GET /listings/{id}/social
    schemas/
      listings.py              MODIFY  — add ExportResponse, SocialPostResponse schemas

alembic/versions/
  005_social_posts_export_bundles.py  CREATE  — new tables

tests/test_agents/
  test_social_content.py       CREATE
  test_mls_export.py           CREATE
tests/test_api/
  test_export.py               CREATE  — export + social endpoint tests
```

---

## Key Patterns

### Social post prompt
```
Generate {platform} post for this real estate listing:
Address: {address}
Features: {beds} bed / {baths} bath / {sqft} sqft / ${price}
Key photos: {top_3_room_labels}
Tone: Professional but engaging. Include relevant hashtags.
```

### MLS export ZIP structure
```
listing-{id}-mls-export.zip
  photos/
    01-hero-exterior.jpg
    02-living-room.jpg
    03-kitchen.jpg
    ...
  metadata.csv        (MLS field mapping: photo_number, room_type, is_hero)
  description.txt     (AI-generated listing description)
```

### Agent constructor pattern (same as all agents)
```python
class SocialContentAgent(BaseAgent):
    agent_name = "social_content"
    def __init__(self, llm_provider=None, session_factory=None):
        self._llm_provider = llm_provider or get_llm_provider()
        self._session_factory = session_factory or AsyncSessionLocal
```

---

## Tasks

---

### Task 1: SocialPost + ExportBundle models + migration

**Files:**
- Create: `src/launchlens/models/social_post.py`
- Create: `src/launchlens/models/export_bundle.py`
- Create: `alembic/versions/005_social_posts_export_bundles.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_agents/test_social_content.py` with a model import test:

```python
# tests/test_agents/test_social_content.py
import pytest


def test_social_post_model_exists():
    from launchlens.models.social_post import SocialPost
    assert hasattr(SocialPost, "listing_id")
    assert hasattr(SocialPost, "platform")
    assert hasattr(SocialPost, "caption")


def test_export_bundle_model_exists():
    from launchlens.models.export_bundle import ExportBundle
    assert hasattr(ExportBundle, "listing_id")
    assert hasattr(ExportBundle, "s3_key")
    assert hasattr(ExportBundle, "format")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_social_content.py -v 2>&1 | tail -10
```

- [ ] **Step 3: Create SocialPost model**

Create `src/launchlens/models/social_post.py`:

```python
import uuid
from sqlalchemy import UUID, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import TenantScopedModel


class SocialPost(TenantScopedModel):
    __tablename__ = "social_posts"
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # instagram, facebook, linkedin, twitter
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    hashtags: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)  # hero photo
```

- [ ] **Step 4: Create ExportBundle model**

Create `src/launchlens/models/export_bundle.py`:

```python
import uuid
from sqlalchemy import UUID, String
from sqlalchemy.orm import Mapped, mapped_column
from .base import TenantScopedModel


class ExportBundle(TenantScopedModel):
    __tablename__ = "export_bundles"
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    format: Mapped[str] = mapped_column(String(50), default="mls_zip")  # mls_zip, social_pack
    file_size_bytes: Mapped[int | None]
```

- [ ] **Step 5: Create migration**

Create `alembic/versions/005_social_posts_export_bundles.py`:

```python
"""social posts and export bundles

Revision ID: 005
Revises: 004
Create Date: 2026-03-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "social_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("caption", sa.Text, nullable=False),
        sa.Column("hashtags", sa.Text, nullable=True),
        sa.Column("image_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.create_table(
        "export_bundles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("format", sa.String(50), nullable=False, server_default="mls_zip"),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
    )

    # Enable RLS
    for table in ("social_posts", "export_bundles"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = current_setting('app.current_tenant')::uuid)
        """)


def downgrade() -> None:
    op.drop_table("export_bundles")
    op.drop_table("social_posts")
```

- [ ] **Step 6: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_social_content.py -v 2>&1 | tail -10
```

- [ ] **Step 7: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/models/social_post.py src/launchlens/models/export_bundle.py alembic/versions/005_social_posts_export_bundles.py tests/test_agents/test_social_content.py && git commit -m "feat: add SocialPost and ExportBundle models with migration"
```

---

### Task 2: SocialContentAgent

**Files:**
- Create: `src/launchlens/agents/social_content.py`
- Modify: `tests/test_agents/test_social_content.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_agents/test_social_content.py`:

```python
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import select
from tests.test_agents.conftest import make_session_factory
from launchlens.agents.base import AgentContext
from launchlens.agents.social_content import SocialContentAgent
from launchlens.models.social_post import SocialPost
from launchlens.models.listing import Listing, ListingState
from launchlens.models.asset import Asset
from launchlens.models.package_selection import PackageSelection


@pytest.fixture
async def listing_with_package(db_session):
    """Create a listing with package selections for social content generation."""
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "500 Social Ave", "city": "Miami", "state": "FL"},
        metadata_={"beds": 4, "baths": 3, "sqft": 2800, "price": 650000},
        state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    # Create an asset and package selection (hero)
    asset = Asset(
        tenant_id=tenant_id, listing_id=listing.id,
        file_path=f"listings/{listing.id}/hero.jpg", file_hash="hero123", state="ingested",
    )
    db_session.add(asset)
    await db_session.flush()

    ps = PackageSelection(
        tenant_id=tenant_id, listing_id=listing.id,
        asset_id=asset.id, channel="mls", position=0,
        composite_score=0.95, selected_by="ai",
    )
    db_session.add(ps)
    await db_session.flush()
    return listing, asset


@pytest.mark.asyncio
async def test_social_content_generates_posts(db_session, listing_with_package):
    listing, asset = listing_with_package
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value='{"caption": "Stunning 4BR/3BA home in Miami! Modern finishes throughout.", "hashtags": "#MiamiRealEstate #JustListed #DreamHome"}')

    agent = SocialContentAgent(
        llm_provider=mock_llm,
        session_factory=make_session_factory(db_session),
    )
    result = await agent.execute(ctx)

    assert result["post_count"] >= 1
    posts = (await db_session.execute(select(SocialPost))).scalars().all()
    assert len(posts) >= 1
    assert all(p.listing_id == listing.id for p in posts)
    assert any(p.platform == "instagram" for p in posts)


@pytest.mark.asyncio
async def test_social_content_emits_event(db_session, listing_with_package):
    listing, _ = listing_with_package
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value='{"caption": "Beautiful home!", "hashtags": "#realestate"}')

    agent = SocialContentAgent(
        llm_provider=mock_llm,
        session_factory=make_session_factory(db_session),
    )
    await agent.execute(ctx)

    from launchlens.models.event import Event
    events = (await db_session.execute(
        select(Event).where(Event.event_type == "social_content.completed")
    )).scalars().all()
    assert len(events) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_social_content.py -k "generates or emits" -v 2>&1 | tail -10
```

- [ ] **Step 3: Implement SocialContentAgent**

Create `src/launchlens/agents/social_content.py`:

```python
import uuid
import json
from sqlalchemy import select

from launchlens.database import AsyncSessionLocal
from launchlens.models.listing import Listing
from launchlens.models.package_selection import PackageSelection
from launchlens.models.social_post import SocialPost
from launchlens.providers import get_llm_provider
from launchlens.services.events import emit_event
from .base import BaseAgent, AgentContext

PLATFORMS = ["instagram", "facebook", "linkedin", "twitter"]

_PROMPT_TEMPLATE = """\
Generate a {platform} post for this real estate listing.

Address: {address}
Features: {features}
Top photos: {photo_descriptions}

Requirements:
- Tone: Professional but engaging, appropriate for {platform}
- Include a compelling hook in the first line
- Mention key selling points
- End with a call to action

Return ONLY valid JSON with two keys:
{{"caption": "your post text here", "hashtags": "#relevant #hashtags #here"}}
"""


class SocialContentAgent(BaseAgent):
    agent_name = "social_content"

    def __init__(self, llm_provider=None, session_factory=None):
        self._llm_provider = llm_provider or get_llm_provider()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)
                if not listing:
                    raise ValueError(f"Listing {listing_id} not found")

                # Get top selections for photo context
                selections = (await session.execute(
                    select(PackageSelection)
                    .where(PackageSelection.listing_id == listing_id)
                    .order_by(PackageSelection.position)
                    .limit(5)
                )).scalars().all()

                photo_descriptions = ", ".join(
                    f"#{s.position}: {s.channel} (score {s.composite_score:.2f})"
                    for s in selections
                ) or "No photos selected yet"

                addr = listing.address
                address_str = f"{addr.get('street', '')}, {addr.get('city', '')}, {addr.get('state', '')}"
                meta = listing.metadata_
                features = f"{meta.get('beds', '?')} bed / {meta.get('baths', '?')} bath / {meta.get('sqft', '?')} sqft / ${meta.get('price', '?'):,}" if meta.get('price') else f"{meta.get('beds', '?')} bed / {meta.get('baths', '?')} bath"

                hero_asset_id = selections[0].asset_id if selections else None

                posts_created = []
                for platform in PLATFORMS:
                    prompt = _PROMPT_TEMPLATE.format(
                        platform=platform,
                        address=address_str,
                        features=features,
                        photo_descriptions=photo_descriptions,
                    )

                    raw = await self._llm_provider.complete(prompt=prompt, context=listing.metadata_)

                    try:
                        data = json.loads(raw)
                        caption = data.get("caption", raw)
                        hashtags = data.get("hashtags", "")
                    except (json.JSONDecodeError, AttributeError):
                        caption = raw
                        hashtags = ""

                    post = SocialPost(
                        tenant_id=listing.tenant_id,
                        listing_id=listing_id,
                        platform=platform,
                        caption=caption,
                        hashtags=hashtags,
                        image_asset_id=hero_asset_id,
                    )
                    session.add(post)
                    posts_created.append(platform)

                await emit_event(
                    session=session,
                    event_type="social_content.completed",
                    payload={"listing_id": str(listing_id), "platforms": posts_created, "post_count": len(posts_created)},
                    tenant_id=str(context.tenant_id),
                    listing_id=str(listing_id),
                )

        return {"post_count": len(posts_created), "platforms": posts_created}
```

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_social_content.py -v 2>&1 | tail -15
```

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/agents/social_content.py tests/test_agents/test_social_content.py && git commit -m "feat: add SocialContentAgent (generates platform-specific social posts)"
```

---

### Task 3: MLSExportAgent

**Files:**
- Create: `src/launchlens/agents/mls_export.py`
- Create: `tests/test_agents/test_mls_export.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_agents/test_mls_export.py`:

```python
# tests/test_agents/test_mls_export.py
import uuid
import pytest
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy import select
from tests.test_agents.conftest import make_session_factory
from launchlens.agents.base import AgentContext
from launchlens.agents.mls_export import MLSExportAgent
from launchlens.models.export_bundle import ExportBundle
from launchlens.models.listing import Listing, ListingState
from launchlens.models.asset import Asset
from launchlens.models.package_selection import PackageSelection
from launchlens.models.vision_result import VisionResult


@pytest.fixture
async def export_listing(db_session):
    """Listing with assets, vision results, and package selections — ready for export."""
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "100 Export Blvd", "city": "Denver", "state": "CO"},
        metadata_={"beds": 3, "baths": 2, "sqft": 1800, "price": 450000},
        state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    assets = []
    for i, room in enumerate(["exterior", "living_room", "kitchen"]):
        a = Asset(
            tenant_id=tenant_id, listing_id=listing.id,
            file_path=f"listings/{listing.id}/{room}.jpg", file_hash=f"hash{i}", state="ingested",
        )
        db_session.add(a)
        assets.append(a)
    await db_session.flush()

    for i, a in enumerate(assets):
        vr = VisionResult(
            tenant_id=tenant_id, asset_id=a.id,
            tier=1, room_label=["exterior", "living_room", "kitchen"][i],
            quality_score=90 - i * 5, commercial_score=80, hero_candidate=(i == 0),
        )
        db_session.add(vr)

        ps = PackageSelection(
            tenant_id=tenant_id, listing_id=listing.id,
            asset_id=a.id, channel="mls", position=i,
            composite_score=0.9 - i * 0.1, selected_by="ai",
        )
        db_session.add(ps)

    await db_session.flush()
    return listing, assets


@pytest.mark.asyncio
async def test_mls_export_creates_bundle(db_session, export_listing):
    listing, assets = export_listing
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_storage = MagicMock()
    mock_storage.upload_bytes = MagicMock(return_value=f"exports/{listing.id}/mls-bundle.zip")

    agent = MLSExportAgent(
        storage_service=mock_storage,
        session_factory=make_session_factory(db_session),
    )
    result = await agent.execute(ctx)

    assert "s3_key" in result
    assert result["photo_count"] == 3
    mock_storage.upload_bytes.assert_called_once()

    # ExportBundle row created
    bundles = (await db_session.execute(select(ExportBundle))).scalars().all()
    assert len(bundles) == 1
    assert bundles[0].listing_id == listing.id
    assert bundles[0].format == "mls_zip"


@pytest.mark.asyncio
async def test_mls_export_emits_event(db_session, export_listing):
    listing, _ = export_listing
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_storage = MagicMock()
    mock_storage.upload_bytes = MagicMock(return_value="exports/test.zip")

    agent = MLSExportAgent(
        storage_service=mock_storage,
        session_factory=make_session_factory(db_session),
    )
    await agent.execute(ctx)

    from launchlens.models.event import Event
    events = (await db_session.execute(
        select(Event).where(Event.event_type == "mls_export.completed")
    )).scalars().all()
    assert len(events) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_mls_export.py -v 2>&1 | tail -10
```

- [ ] **Step 3: Implement MLSExportAgent**

Create `src/launchlens/agents/mls_export.py`:

```python
import uuid
import io
import csv
import zipfile
from sqlalchemy import select

from launchlens.database import AsyncSessionLocal
from launchlens.models.listing import Listing
from launchlens.models.asset import Asset
from launchlens.models.package_selection import PackageSelection
from launchlens.models.vision_result import VisionResult
from launchlens.models.export_bundle import ExportBundle
from launchlens.services.storage import StorageService
from launchlens.services.events import emit_event
from .base import BaseAgent, AgentContext


class MLSExportAgent(BaseAgent):
    agent_name = "mls_export"

    def __init__(self, storage_service=None, session_factory=None):
        self._storage = storage_service or StorageService()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)
                if not listing:
                    raise ValueError(f"Listing {listing_id} not found")

                # Get package selections with asset info
                selections = (await session.execute(
                    select(PackageSelection, Asset)
                    .join(Asset, PackageSelection.asset_id == Asset.id)
                    .where(PackageSelection.listing_id == listing_id)
                    .order_by(PackageSelection.position)
                )).all()

                # Get vision results for room labels
                asset_ids = [s[1].id for s in selections]
                vision_results = {}
                if asset_ids:
                    vrs = (await session.execute(
                        select(VisionResult).where(
                            VisionResult.asset_id.in_(asset_ids),
                            VisionResult.tier == 1,
                        )
                    )).scalars().all()
                    vision_results = {vr.asset_id: vr for vr in vrs}

                # Build ZIP in memory
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    # Add metadata CSV
                    csv_buffer = io.StringIO()
                    writer = csv.writer(csv_buffer)
                    writer.writerow(["photo_number", "filename", "room_type", "is_hero", "quality_score"])

                    for i, (ps, asset) in enumerate(selections):
                        vr = vision_results.get(asset.id)
                        room_label = vr.room_label if vr else "unknown"
                        is_hero = "yes" if ps.position == 0 else "no"
                        quality = vr.quality_score if vr else 0

                        # Photo filename: XX-room_type.jpg
                        filename = f"{i + 1:02d}-{room_label}.jpg"
                        writer.writerow([i + 1, filename, room_label, is_hero, quality])

                        # Add photo path reference (actual file download is client-side from S3)
                        zf.writestr(f"photos/{filename}", f"[S3 reference: {asset.file_path}]")

                    zf.writestr("metadata.csv", csv_buffer.getvalue())

                    # Add listing description if content was generated
                    addr = listing.address
                    meta = listing.metadata_
                    desc = f"Property: {addr.get('street', '')}, {addr.get('city', '')}, {addr.get('state', '')}\n"
                    desc += f"Features: {meta.get('beds', '?')} bed / {meta.get('baths', '?')} bath / {meta.get('sqft', '?')} sqft\n"
                    desc += f"Price: ${meta.get('price', 0):,}\n"
                    zf.writestr("description.txt", desc)

                zip_bytes = zip_buffer.getvalue()

                # Upload to S3
                s3_key = self._storage.upload_bytes(
                    data=zip_bytes,
                    key=f"exports/{listing_id}/mls-bundle.zip",
                    content_type="application/zip",
                )

                # Create ExportBundle record
                bundle = ExportBundle(
                    tenant_id=listing.tenant_id,
                    listing_id=listing_id,
                    s3_key=s3_key,
                    format="mls_zip",
                    file_size_bytes=len(zip_bytes),
                )
                session.add(bundle)

                await emit_event(
                    session=session,
                    event_type="mls_export.completed",
                    payload={
                        "listing_id": str(listing_id),
                        "s3_key": s3_key,
                        "photo_count": len(selections),
                        "file_size_bytes": len(zip_bytes),
                    },
                    tenant_id=str(context.tenant_id),
                    listing_id=str(listing_id),
                )

        return {
            "s3_key": s3_key,
            "photo_count": len(selections),
            "file_size_bytes": len(zip_bytes),
        }
```

**Note:** The `StorageService` needs an `upload_bytes` method. Read `src/launchlens/services/storage.py` first — if it only has `upload(file_path, key)`, add `upload_bytes(data, key, content_type)`. If mocking in tests, just mock `upload_bytes` directly.

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_mls_export.py -v 2>&1 | tail -15
```

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/agents/mls_export.py tests/test_agents/test_mls_export.py && git commit -m "feat: add MLSExportAgent (ZIP packaging with metadata CSV)"
```

---

### Task 4: Wire into pipeline + export API endpoint + tag

**Files:**
- Modify: `src/launchlens/activities/pipeline.py`
- Modify: `src/launchlens/workflows/listing_pipeline.py`
- Modify: `src/launchlens/api/listings.py`
- Modify: `src/launchlens/api/schemas/listings.py`
- Create: `tests/test_api/test_export.py`

- [ ] **Step 1: Write failing endpoint tests**

Create `tests/test_api/test_export.py`:

```python
# tests/test_api/test_export.py
import uuid
import pytest
from httpx import AsyncClient
import jwt as pyjwt
from launchlens.config import settings


async def _register(client: AsyncClient) -> tuple[str, str]:
    email = f"test-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Tester", "company_name": "TestCo"
    })
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_export_not_ready(async_client: AsyncClient):
    """GET /listings/{id}/export returns 404 when no export bundle exists."""
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "No Export St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    resp = await async_client.get(f"/listings/{listing_id}/export", headers=_auth(token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_social_posts_empty(async_client: AsyncClient):
    """GET /listings/{id}/social returns empty list when no posts exist."""
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "No Social St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    resp = await async_client.get(f"/listings/{listing_id}/social", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_export_requires_auth(async_client: AsyncClient):
    resp = await async_client.get(f"/listings/{uuid.uuid4()}/export")
    assert resp.status_code == 401
```

- [ ] **Step 2: Add activities for new agents**

In `src/launchlens/activities/pipeline.py`, add:

```python
@activity.defn
async def run_social_content(context: AgentContext) -> dict:
    from launchlens.agents.social_content import SocialContentAgent
    return await SocialContentAgent().execute(context)


@activity.defn
async def run_mls_export(context: AgentContext) -> dict:
    from launchlens.agents.mls_export import MLSExportAgent
    return await MLSExportAgent().execute(context)
```

Add both to `ALL_ACTIVITIES` list.

- [ ] **Step 3: Wire into workflow**

In `src/launchlens/workflows/listing_pipeline.py`, add imports for `run_social_content` and `run_mls_export` in the `imports_passed_through` block. Add them to Phase 2, after `run_brand` and before `run_distribution`:

```python
        # Phase 2: Post-approval pipeline
        await workflow.execute_activity(run_content, ctx, ...)
        await workflow.execute_activity(run_brand, ctx, ...)
        await workflow.execute_activity(run_social_content, ctx, ...)
        await workflow.execute_activity(run_mls_export, ctx, ...)
        await workflow.execute_activity(run_distribution, ctx, ...)
```

- [ ] **Step 4: Add export + social endpoints to listings router**

In `src/launchlens/api/listings.py`, add:

```python
from launchlens.models.export_bundle import ExportBundle
from launchlens.models.social_post import SocialPost


@router.get("/{listing_id}/export")
async def get_export(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = (await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == current_user.tenant_id)
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    bundle = (await db.execute(
        select(ExportBundle)
        .where(ExportBundle.listing_id == listing.id)
        .order_by(ExportBundle.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    if not bundle:
        raise HTTPException(status_code=404, detail="Export not ready — approve the listing first")

    return {
        "s3_key": bundle.s3_key,
        "format": bundle.format,
        "file_size_bytes": bundle.file_size_bytes,
        "created_at": bundle.created_at.isoformat(),
    }


@router.get("/{listing_id}/social")
async def get_social_posts(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = (await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == current_user.tenant_id)
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    posts = (await db.execute(
        select(SocialPost).where(SocialPost.listing_id == listing.id).order_by(SocialPost.platform)
    )).scalars().all()

    return [
        {
            "platform": p.platform,
            "caption": p.caption,
            "hashtags": p.hashtags,
            "image_asset_id": str(p.image_asset_id) if p.image_asset_id else None,
        }
        for p in posts
    ]
```

- [ ] **Step 5: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_export.py tests/test_agents/test_social_content.py tests/test_agents/test_mls_export.py -v 2>&1 | tail -20
```

- [ ] **Step 6: Run full suite**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest --tb=short -q 2>&1 | tail -5
```

- [ ] **Step 7: Commit and tag**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/activities/pipeline.py src/launchlens/workflows/listing_pipeline.py src/launchlens/api/listings.py tests/test_api/test_export.py && git commit -m "feat: wire new agents into pipeline + add export/social API endpoints" && git tag v0.9.0-new-agents && echo "Tagged v0.9.0-new-agents"
```

---

## NOT in scope

- Actual S3 file download in the ZIP (currently stores path references — real download is client-side from S3 presigned URLs)
- Social media scheduling / direct posting (export-only for MVP)
- Email blast generation (deferred)
- Property website generation (deferred)
- MLS browser automation (Phase 2)
- Image resizing for MLS specs (deferred — would need Pillow)

## What already exists

- All 8 existing agents with session injection + Outbox pattern
- ContentAgent (Claude-powered description generation) — SocialContentAgent follows same pattern
- BrandAgent (S3 upload) — MLSExportAgent follows same pattern
- StorageService with `upload` method (may need `upload_bytes` added)
- `ALL_ACTIVITIES` list and Temporal workflow with Phase 1/Phase 2 structure
- Package selections with position, composite_score, channel
- VisionResult with room_label, quality_score for metadata CSV
