# Video Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a complete video pipeline with three tracks — AI-generated property tours (Kling), user-submitted video processing, and professional video showcase with auto-chapters and social cuts — so every listing can have video content regardless of budget.

**Architecture:** A `VideoAsset` model stores all video types. `VideoAgent` ports the Kling image-to-video pipeline from Juke Marketing Engine (room prompts, camera control, FFmpeg stitching). `ChapterAgent` uses GPT-4V on extracted keyframes to auto-generate chapter markers. `SocialCutAgent` uses FFmpeg scene detection to create platform-specific clips. Video upload and retrieval endpoints round out the API. All agents follow the existing `BaseAgent` pattern.

**Tech Stack:** Kling AI API (image-to-video), FFmpeg (stitching, transcoding, scene detection, cropping), GPT-4V (chapter analysis), S3 (storage), SQLAlchemy 2.0 async

---

## File Structure

```
src/launchlens/
  models/
    video_asset.py              CREATE  — VideoAsset model (listing_id, type, chapters, social_cuts)

  providers/
    kling.py                    CREATE  — KlingProvider (JWT auth, image-to-video API, polling)

  services/
    video_stitcher.py           CREATE  — FFmpeg stitching (clips → final video with transitions + music)

  agents/
    video.py                    CREATE  — VideoAgent (Kling pipeline: select photos → generate clips → stitch)
    video_prompts.py            CREATE  — Room prompts, camera control, feature tags (ported from Juke)
    chapter.py                  CREATE  — ChapterAgent (GPT-4V keyframe analysis → chapter markers)
    social_cuts.py              CREATE  — SocialCutAgent (FFmpeg scene detect → platform clips)

  api/
    listings.py                 MODIFY  — add video upload, GET video, GET social-cuts endpoints

  config.py                     MODIFY  — add Kling + video config fields

alembic/versions/
  007_video_assets.py           CREATE  — video_assets table

tests/test_agents/
  test_video.py                 CREATE
  test_chapter.py               CREATE
  test_social_cuts.py           CREATE
tests/test_api/
  test_video.py                 CREATE  — video endpoint tests
```

---

## Key Design Decisions

### Kling vs. Runway vs. Synthesia
We use **Kling** because we already have a production-tested pipeline in Juke Marketing Engine. Kling costs ~$0.02-0.05 per 5-second clip (vs. Runway at $0.10-0.50). We have 16 room-specific prompts, camera controls, and feature tag enrichment already built.

### Three video types in one model
```python
video_type: "ai_generated" | "user_raw" | "professional"
```
All three types share the same model — they diverge in processing pipeline but converge on output (chapters, social cuts, branded player).

### VideoAgent runs parallel to human review
While the user reviews photos (AWAITING_REVIEW → IN_REVIEW), the VideoAgent generates the property tour in the background. By approval time, the video is ready.

### Social cuts are platform-specific
Each platform gets optimized output:
- Instagram Reel: 15-30s, 9:16 vertical, 1080x1920
- TikTok: 15-60s, 9:16 vertical, 1080x1920
- Facebook: 30-60s, 16:9 horizontal, 1920x1080
- YouTube Short: ≤60s, 9:16 vertical, 1080x1920

### FFmpeg is the workhorse
No cloud transcoding service needed for MVP. FFmpeg handles:
- Clip normalization (resolution, codec)
- Xfade transitions between clips
- Music overlay with fade-out
- Scene detection on pro videos
- Crop + resize for social formats
- Thumbnail extraction

---

## Room Prompts (Ported from Juke)

```python
ROOM_PROMPTS = {
    "drone":            "Slow cinematic aerial drift over property, stable horizon, golden hour light",
    "exterior":         "Slow cinematic dolly toward front entrance, warm natural light, professional real estate",
    "exterior_rear":    "Slow cinematic dolly across backyard, natural light, inviting atmosphere",
    "living_room":      "Slow cinematic dolly through living room, warm natural light, spacious feel",
    "kitchen":          "Slow cinematic dolly into kitchen, warm natural light, modern finishes",
    "bedroom":          "Slow cinematic pan across bedroom, soft natural light, peaceful atmosphere",
    "primary_bedroom":  "Slow cinematic dolly into primary suite, soft natural light, luxurious feel",
    "bathroom":         "Slow cinematic dolly into bathroom, clean bright light, spa-like atmosphere",
    "primary_bathroom": "Slow cinematic pan across primary bath, bright clean light, luxury finishes",
    "dining_room":      "Slow cinematic dolly through dining area, warm ambient light, elegant setting",
    "office":           "Slow cinematic pan across office, natural light, productive atmosphere",
    "garage":           "Slow cinematic dolly into garage, even lighting, spacious layout",
    "pool":             "Slow cinematic drift over pool area, shimmering water, resort atmosphere",
    "backyard":         "Slow cinematic pan across backyard, natural light, outdoor living space",
    "entryway":         "Slow cinematic dolly through entryway, welcoming light, grand entrance",
    "basement":         "Slow cinematic dolly through basement, even lighting, finished space",
}

ROOM_CAMERA_CONTROLS = {
    "drone":            {"zoom": 2, "horizontal": 3},
    "exterior":         {"zoom": 4, "horizontal": 0},
    "exterior_rear":    {"zoom": 3, "horizontal": 2},
    "living_room":      {"zoom": 4, "horizontal": -2},
    "kitchen":          {"zoom": 5, "horizontal": 0},
    "bedroom":          {"zoom": 3, "horizontal": -3},
    "primary_bedroom":  {"zoom": 4, "horizontal": -2},
    "bathroom":         {"zoom": 3, "horizontal": 0},
    "primary_bathroom": {"zoom": 3, "horizontal": 2},
    "dining_room":      {"zoom": 4, "horizontal": -2},
    "office":           {"zoom": 3, "horizontal": 3},
    "garage":           {"zoom": 3, "horizontal": 0},
    "pool":             {"zoom": 2, "horizontal": 3},
    "backyard":         {"zoom": 2, "horizontal": -3},
    "entryway":         {"zoom": 5, "horizontal": 0},
    "basement":         {"zoom": 4, "horizontal": 0},
}

NEGATIVE_PROMPT = "shaky camera, fast cuts, blurry, distorted, excessive movement, hallucinated spaces, morphing, artifacts"
```

---

## Tasks

---

### Task 1: VideoAsset model + config + migration

**Files:**
- Create: `src/launchlens/models/video_asset.py`
- Modify: `src/launchlens/config.py`
- Create: `alembic/versions/007_video_assets.py`
- Create: `tests/test_agents/test_video.py` (model test only)

- [ ] **Step 1: Write failing test**

Create `tests/test_agents/test_video.py`:

```python
# tests/test_agents/test_video.py
import pytest


def test_video_asset_model_exists():
    from launchlens.models.video_asset import VideoAsset
    assert hasattr(VideoAsset, "listing_id")
    assert hasattr(VideoAsset, "video_type")
    assert hasattr(VideoAsset, "chapters")
    assert hasattr(VideoAsset, "social_cuts")
    assert hasattr(VideoAsset, "status")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_video.py -v 2>&1 | tail -10
```

- [ ] **Step 3: Create VideoAsset model**

Create `src/launchlens/models/video_asset.py`:

```python
import uuid
from sqlalchemy import UUID, String, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base import TenantScopedModel


class VideoAsset(TenantScopedModel):
    __tablename__ = "video_assets"
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    video_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ai_generated, user_raw, professional
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="processing")  # uploading, processing, ready, failed
    chapters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # [{"time": 0, "label": "exterior"}, ...]
    social_cuts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # [{"platform": "instagram", "s3_key": "...", "duration": 15}, ...]
    branded_player_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # {logo_url, cta_text, accent_color}
    thumbnail_s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    clip_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

- [ ] **Step 4: Add Kling + video config fields**

Read `src/launchlens/config.py` first. Add after the provider API keys section:

```python
    # Video (Kling AI)
    kling_access_key: str = ""
    kling_secret_key: str = ""
    kling_api_base_url: str = "https://api.klingai.com"
    video_max_photos: int = 8
    video_score_floor: float = 0.65
    video_clip_duration: int = 5
```

- [ ] **Step 5: Create migration**

Check latest migration revision first (`ls alembic/versions/`). Create migration with correct revision chain:

```python
"""video assets

Revision ID: 007
Revises: 006
Create Date: 2026-03-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "video_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("video_type", sa.String(50), nullable=False),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="processing"),
        sa.Column("chapters", postgresql.JSONB, nullable=True),
        sa.Column("social_cuts", postgresql.JSONB, nullable=True),
        sa.Column("branded_player_config", postgresql.JSONB, nullable=True),
        sa.Column("thumbnail_s3_key", sa.String(500), nullable=True),
        sa.Column("clip_count", sa.Integer, nullable=True),
    )

    op.execute("ALTER TABLE video_assets ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON video_assets
        USING (tenant_id = current_setting('app.current_tenant')::uuid)
    """)


def downgrade() -> None:
    op.drop_table("video_assets")
```

- [ ] **Step 6: Run test**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_video.py -v 2>&1 | tail -10
```

- [ ] **Step 7: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/models/video_asset.py src/launchlens/config.py alembic/versions/007_video_assets.py tests/test_agents/test_video.py && git commit -m "feat: add VideoAsset model, Kling config, and migration"
```

---

### Task 2: Kling provider + video prompts

**Files:**
- Create: `src/launchlens/providers/kling.py`
- Create: `src/launchlens/agents/video_prompts.py`
- Create: `tests/test_providers/test_kling.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_providers/test_kling.py`:

```python
# tests/test_providers/test_kling.py
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


def test_kling_provider_exists():
    from launchlens.providers.kling import KlingProvider
    assert hasattr(KlingProvider, "generate_clip")
    assert hasattr(KlingProvider, "poll_task")


def test_video_prompts_exist():
    from launchlens.agents.video_prompts import ROOM_PROMPTS, ROOM_CAMERA_CONTROLS, NEGATIVE_PROMPT
    assert "kitchen" in ROOM_PROMPTS
    assert "living_room" in ROOM_PROMPTS
    assert "exterior" in ROOM_PROMPTS
    assert "kitchen" in ROOM_CAMERA_CONTROLS
    assert "zoom" in ROOM_CAMERA_CONTROLS["kitchen"]
    assert len(NEGATIVE_PROMPT) > 0


def test_kling_jwt_generation():
    from launchlens.providers.kling import KlingProvider
    provider = KlingProvider(access_key="test_ak", secret_key="test_sk")
    token = provider._generate_jwt()
    assert isinstance(token, str)
    assert len(token) > 0


@pytest.mark.asyncio
@patch("launchlens.providers.kling.httpx.AsyncClient")
async def test_kling_generate_clip_submits_task(MockClient):
    from launchlens.providers.kling import KlingProvider

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"code": 0, "data": {"task_id": "task_123"}}

    mock_client_instance = AsyncMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
    MockClient.return_value = mock_client_instance

    provider = KlingProvider(access_key="test_ak", secret_key="test_sk")
    task_id = await provider.generate_clip(
        image_url="https://example.com/photo.jpg",
        prompt="Slow cinematic dolly into kitchen",
        negative_prompt="shaky camera",
        camera_control={"zoom": 5, "horizontal": 0},
    )
    assert task_id == "task_123"


@pytest.mark.asyncio
@patch("launchlens.providers.kling.httpx.AsyncClient")
async def test_kling_poll_task_returns_url(MockClient):
    from launchlens.providers.kling import KlingProvider

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "code": 0,
        "data": {
            "task_status": "succeed",
            "task_result": {"videos": [{"url": "https://cdn.kling.ai/video.mp4", "duration": "5"}]},
        },
    }

    mock_client_instance = AsyncMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
    MockClient.return_value = mock_client_instance

    provider = KlingProvider(access_key="test_ak", secret_key="test_sk")
    url = await provider.poll_task("task_123", timeout=10, interval=1)
    assert url == "https://cdn.kling.ai/video.mp4"
```

- [ ] **Step 2: Create video prompts module**

Create `src/launchlens/agents/video_prompts.py`:

```python
"""Room-specific prompts and camera controls for Kling AI video generation.
Ported from Juke Marketing Engine.
"""

ROOM_PROMPTS: dict[str, str] = {
    "drone": "Slow cinematic aerial drift over property, stable horizon, golden hour light",
    "exterior": "Slow cinematic dolly toward front entrance, warm natural light, professional real estate",
    "exterior_rear": "Slow cinematic dolly across backyard, natural light, inviting atmosphere",
    "living_room": "Slow cinematic dolly through living room, warm natural light, spacious feel",
    "kitchen": "Slow cinematic dolly into kitchen, warm natural light, modern finishes",
    "bedroom": "Slow cinematic pan across bedroom, soft natural light, peaceful atmosphere",
    "primary_bedroom": "Slow cinematic dolly into primary suite, soft natural light, luxurious feel",
    "bathroom": "Slow cinematic dolly into bathroom, clean bright light, spa-like atmosphere",
    "primary_bathroom": "Slow cinematic pan across primary bath, bright clean light, luxury finishes",
    "dining_room": "Slow cinematic dolly through dining area, warm ambient light, elegant setting",
    "office": "Slow cinematic pan across office, natural light, productive atmosphere",
    "garage": "Slow cinematic dolly into garage, even lighting, spacious layout",
    "pool": "Slow cinematic drift over pool area, shimmering water, resort atmosphere",
    "backyard": "Slow cinematic pan across backyard, natural light, outdoor living space",
    "entryway": "Slow cinematic dolly through entryway, welcoming light, grand entrance",
    "basement": "Slow cinematic dolly through basement, even lighting, finished space",
}

ROOM_CAMERA_CONTROLS: dict[str, dict[str, int]] = {
    "drone": {"zoom": 2, "horizontal": 3},
    "exterior": {"zoom": 4, "horizontal": 0},
    "exterior_rear": {"zoom": 3, "horizontal": 2},
    "living_room": {"zoom": 4, "horizontal": -2},
    "kitchen": {"zoom": 5, "horizontal": 0},
    "bedroom": {"zoom": 3, "horizontal": -3},
    "primary_bedroom": {"zoom": 4, "horizontal": -2},
    "bathroom": {"zoom": 3, "horizontal": 0},
    "primary_bathroom": {"zoom": 3, "horizontal": 2},
    "dining_room": {"zoom": 4, "horizontal": -2},
    "office": {"zoom": 3, "horizontal": 3},
    "garage": {"zoom": 3, "horizontal": 0},
    "pool": {"zoom": 2, "horizontal": 3},
    "backyard": {"zoom": 2, "horizontal": -3},
    "entryway": {"zoom": 5, "horizontal": 0},
    "basement": {"zoom": 4, "horizontal": 0},
}

NEGATIVE_PROMPT = "shaky camera, fast cuts, blurry, distorted, excessive movement, hallucinated spaces, morphing, artifacts"

# Feature tags that enhance prompts when detected in listing metadata
FEATURE_TAGS: dict[str, list[str]] = {
    "kitchen": ["island", "quartz_counters", "granite_counters", "stainless_appliances"],
    "bathroom": ["soaking_tub", "walk_in_shower", "double_vanity"],
    "living_room": ["vaulted_ceilings", "fireplace", "hardwood_floors", "built_ins"],
    "exterior": ["pool", "outdoor_kitchen", "fire_pit", "deck", "patio"],
    "bedroom": ["walk_in_closet", "tray_ceiling"],
    "basement": ["theater", "gym", "wet_bar"],
}

# Transition types between clips (ported from Juke)
TRANSITION_SEQUENCE = [
    "fade",        # drone/exterior → first interior
    "fadeblack",   # exterior → interior transition
    "wipeleft",    # interior → interior
    "wipeleft",    # interior → interior
    "wipeleft",    # interior → interior
    "wipeleft",    # interior → interior
    "fade",        # penultimate → last
    "fade",        # last clip fade out
]

# Photo selection slot order (which rooms get priority)
SLOT_ORDER = [
    "drone", "exterior", "entryway", "living_room", "kitchen",
    "primary_bedroom", "primary_bathroom", "dining_room",
    "office", "bedroom", "bathroom", "basement",
    "backyard", "pool", "garage",
]


def get_prompt_for_room(room_label: str, metadata: dict | None = None) -> str:
    """Get the cinematic prompt for a room, optionally enriched with feature tags."""
    base = ROOM_PROMPTS.get(room_label, ROOM_PROMPTS.get("living_room"))
    if metadata and room_label in FEATURE_TAGS:
        features = [f for f in FEATURE_TAGS[room_label] if metadata.get(f)]
        if features:
            base += f", featuring {', '.join(features)}"
    return base


def get_camera_control(room_label: str) -> dict[str, int]:
    """Get camera control settings for a room."""
    return ROOM_CAMERA_CONTROLS.get(room_label, {"zoom": 3, "horizontal": 0})


def get_transition(clip_index: int, total_clips: int) -> str:
    """Get the transition type for a given clip position."""
    if clip_index >= len(TRANSITION_SEQUENCE):
        return "wipeleft"
    return TRANSITION_SEQUENCE[clip_index]
```

- [ ] **Step 3: Create Kling provider**

Create `src/launchlens/providers/kling.py`:

```python
"""Kling AI image-to-video provider.
Ported from Juke Marketing Engine (app/services/video_generator.py).
"""

import time
import asyncio
import jwt as pyjwt
import httpx
from launchlens.config import settings


class KlingProvider:
    def __init__(
        self,
        access_key: str | None = None,
        secret_key: str | None = None,
        base_url: str | None = None,
    ):
        self._access_key = access_key or settings.kling_access_key
        self._secret_key = secret_key or settings.kling_secret_key
        self._base_url = base_url or settings.kling_api_base_url

    def _generate_jwt(self) -> str:
        now = int(time.time())
        payload = {
            "iss": self._access_key,
            "exp": now + 1800,  # 30 minutes
            "nbf": now - 5,
        }
        return pyjwt.encode(payload, self._secret_key, algorithm="HS256")

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._generate_jwt()}",
        }

    async def generate_clip(
        self,
        image_url: str,
        prompt: str,
        negative_prompt: str = "",
        camera_control: dict | None = None,
        duration: int = 5,
        mode: str = "pro",
    ) -> str:
        """Submit an image-to-video task to Kling. Returns task_id."""
        body: dict = {
            "model_name": "kling-v1",
            "image": image_url,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "cfg_scale": 0.5,
            "mode": mode,
            "duration": str(duration),
        }
        if camera_control:
            body["camera_control"] = {
                "type": "simple",
                "config": {
                    "horizontal": camera_control.get("horizontal", 0),
                    "vertical": 0,
                    "zoom": camera_control.get("zoom", 3),
                    "tilt": 0,
                    "pan": 0,
                    "roll": 0,
                },
            }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self._base_url}/v1/videos/image2video",
                headers=self._headers(),
                json=body,
            )
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Kling API error: {data}")
            return data["data"]["task_id"]

    async def poll_task(
        self,
        task_id: str,
        timeout: int = 300,
        interval: int = 5,
    ) -> str | None:
        """Poll a Kling task until completion. Returns video URL or None on timeout."""
        start = time.time()
        async with httpx.AsyncClient(timeout=30) as client:
            while time.time() - start < timeout:
                resp = await client.get(
                    f"{self._base_url}/v1/videos/image2video/{task_id}",
                    headers=self._headers(),
                )
                data = resp.json()
                status = data.get("data", {}).get("task_status")

                if status == "succeed":
                    videos = data["data"].get("task_result", {}).get("videos", [])
                    return videos[0]["url"] if videos else None
                elif status == "failed":
                    return None

                await asyncio.sleep(interval)
        return None  # Timeout
```

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_providers/test_kling.py tests/test_agents/test_video.py -v 2>&1 | tail -15
```

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/providers/kling.py src/launchlens/agents/video_prompts.py tests/test_providers/test_kling.py && git commit -m "feat: add Kling provider and video prompts (ported from Juke)"
```

---

### Task 3: VideoAgent (AI-generated property tour)

**Files:**
- Create: `src/launchlens/services/video_stitcher.py`
- Create: `src/launchlens/agents/video.py`
- Modify: `tests/test_agents/test_video.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_agents/test_video.py`:

```python
import uuid
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select
from tests.test_agents.conftest import make_session_factory
from launchlens.agents.base import AgentContext
from launchlens.agents.video import VideoAgent
from launchlens.models.video_asset import VideoAsset
from launchlens.models.listing import Listing, ListingState
from launchlens.models.asset import Asset
from launchlens.models.vision_result import VisionResult
from launchlens.models.package_selection import PackageSelection


@pytest.fixture
async def listing_for_video(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "100 Video Ln", "city": "Miami", "state": "FL"},
        metadata_={"beds": 3, "baths": 2, "sqft": 2000, "price": 500000},
        state=ListingState.AWAITING_REVIEW,
    )
    db_session.add(listing)
    await db_session.flush()

    rooms = ["exterior", "living_room", "kitchen"]
    assets = []
    for i, room in enumerate(rooms):
        a = Asset(
            tenant_id=tenant_id, listing_id=listing.id,
            file_path=f"listings/{listing.id}/{room}.jpg", file_hash=f"vid{i}", state="ingested",
        )
        db_session.add(a)
        assets.append(a)
    await db_session.flush()

    for i, (a, room) in enumerate(zip(assets, rooms)):
        vr = VisionResult(
            tenant_id=tenant_id, asset_id=a.id, tier=1,
            room_label=room, quality_score=90 - i * 5, commercial_score=80,
            hero_candidate=(i == 0),
        )
        db_session.add(vr)
        ps = PackageSelection(
            tenant_id=tenant_id, listing_id=listing.id, asset_id=a.id,
            channel="mls", position=i, composite_score=0.9 - i * 0.1, selected_by="ai",
        )
        db_session.add(ps)

    await db_session.flush()
    return listing, assets


@pytest.mark.asyncio
async def test_video_agent_creates_video_asset(db_session, listing_for_video):
    listing, assets = listing_for_video
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_kling = MagicMock()
    mock_kling.generate_clip = AsyncMock(return_value="task_001")
    mock_kling.poll_task = AsyncMock(return_value="https://cdn.kling.ai/clip.mp4")

    mock_storage = MagicMock()
    mock_storage.upload_bytes = MagicMock(return_value=f"videos/{listing.id}/tour.mp4")

    mock_stitcher = MagicMock()
    mock_stitcher.stitch = MagicMock(return_value=b"fake-mp4-bytes")

    agent = VideoAgent(
        kling_provider=mock_kling,
        storage_service=mock_storage,
        video_stitcher=mock_stitcher,
        session_factory=make_session_factory(db_session),
    )
    result = await agent.execute(ctx)

    assert result["status"] == "ready"
    assert result["clip_count"] == 3
    assert "video_asset_id" in result

    videos = (await db_session.execute(select(VideoAsset))).scalars().all()
    assert len(videos) == 1
    assert videos[0].video_type == "ai_generated"
    assert videos[0].status == "ready"
    assert videos[0].clip_count == 3


@pytest.mark.asyncio
async def test_video_agent_emits_event(db_session, listing_for_video):
    listing, _ = listing_for_video
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_kling = MagicMock()
    mock_kling.generate_clip = AsyncMock(return_value="task_001")
    mock_kling.poll_task = AsyncMock(return_value="https://cdn.kling.ai/clip.mp4")
    mock_storage = MagicMock()
    mock_storage.upload_bytes = MagicMock(return_value="videos/test.mp4")
    mock_stitcher = MagicMock()
    mock_stitcher.stitch = MagicMock(return_value=b"fake-mp4")

    agent = VideoAgent(
        kling_provider=mock_kling, storage_service=mock_storage,
        video_stitcher=mock_stitcher, session_factory=make_session_factory(db_session),
    )
    await agent.execute(ctx)

    from launchlens.models.event import Event
    events = (await db_session.execute(
        select(Event).where(Event.event_type == "video.completed")
    )).scalars().all()
    assert len(events) == 1


@pytest.mark.asyncio
async def test_video_agent_handles_no_selections(db_session):
    """Listing with no package selections → skips video."""
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id, address={"street": "Empty St"}, metadata_={},
        state=ListingState.AWAITING_REVIEW,
    )
    db_session.add(listing)
    await db_session.flush()

    mock_kling = MagicMock()
    agent = VideoAgent(
        kling_provider=mock_kling, storage_service=MagicMock(),
        video_stitcher=MagicMock(), session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)
    assert result.get("skipped") is True
```

- [ ] **Step 2: Create video stitcher service**

Create `src/launchlens/services/video_stitcher.py`:

```python
"""FFmpeg-based video stitcher with transitions and music overlay.
Ported from Juke Marketing Engine.
"""

import subprocess
import tempfile
import os
from pathlib import Path


class VideoStitcher:
    def __init__(self, transition_duration: float = 0.5, music_volume: float = 0.2):
        self._transition_duration = transition_duration
        self._music_volume = music_volume

    def stitch(
        self,
        clip_paths: list[str],
        transitions: list[str],
        music_path: str | None = None,
        output_width: int = 1280,
        output_height: int = 720,
    ) -> bytes:
        """Stitch clips into a single video with transitions and optional music.
        Returns the final video as bytes.
        """
        if not clip_paths:
            raise ValueError("No clips to stitch")

        if len(clip_paths) == 1:
            with open(clip_paths[0], "rb") as f:
                return f.read()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.mp4")

            # Build FFmpeg filter graph with xfade transitions
            inputs = []
            for clip in clip_paths:
                inputs.extend(["-i", clip])

            filter_parts = []
            # Normalize all clips
            for i in range(len(clip_paths)):
                filter_parts.append(
                    f"[{i}:v]scale={output_width}:{output_height}:force_original_aspect_ratio=decrease,"
                    f"pad={output_width}:{output_height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}];"
                )

            # Chain xfade transitions
            prev = "v0"
            for i in range(1, len(clip_paths)):
                transition = transitions[i - 1] if i - 1 < len(transitions) else "fade"
                offset = i * 5 - self._transition_duration * i  # 5s per clip minus overlap
                out = f"xf{i}"
                filter_parts.append(
                    f"[{prev}][v{i}]xfade=transition={transition}:duration={self._transition_duration}:offset={offset:.1f}[{out}];"
                )
                prev = out

            filter_graph = "".join(filter_parts).rstrip(";")

            cmd = ["ffmpeg", "-y"] + inputs + [
                "-filter_complex", filter_graph,
                "-map", f"[{prev}]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
            ]

            # Add music if provided
            if music_path and os.path.exists(music_path):
                cmd.extend([
                    "-i", music_path,
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-shortest",
                ])

            cmd.extend([output_path])

            subprocess.run(cmd, capture_output=True, check=True)

            with open(output_path, "rb") as f:
                return f.read()
```

- [ ] **Step 3: Implement VideoAgent**

Create `src/launchlens/agents/video.py`:

```python
"""VideoAgent — generates AI property tour videos from listing photos via Kling.
Ported from Juke Marketing Engine with adaptations for LaunchLens pipeline.
"""

import uuid
import asyncio
import tempfile
import os
import httpx
from sqlalchemy import select

from launchlens.database import AsyncSessionLocal
from launchlens.models.listing import Listing
from launchlens.models.asset import Asset
from launchlens.models.package_selection import PackageSelection
from launchlens.models.vision_result import VisionResult
from launchlens.models.video_asset import VideoAsset
from launchlens.providers.kling import KlingProvider
from launchlens.services.storage import StorageService
from launchlens.services.video_stitcher import VideoStitcher
from launchlens.services.events import emit_event
from launchlens.agents.video_prompts import (
    get_prompt_for_room, get_camera_control, get_transition,
    NEGATIVE_PROMPT, SLOT_ORDER,
)
from launchlens.config import settings
from .base import BaseAgent, AgentContext


class VideoAgent(BaseAgent):
    agent_name = "video"

    def __init__(
        self,
        kling_provider=None,
        storage_service=None,
        video_stitcher=None,
        session_factory=None,
    ):
        self._kling = kling_provider or KlingProvider()
        self._storage = storage_service or StorageService()
        self._stitcher = video_stitcher or VideoStitcher()
        self._session_factory = session_factory or AsyncSessionLocal
        self._max_photos = settings.video_max_photos
        self._score_floor = settings.video_score_floor
        self._semaphore = asyncio.Semaphore(3)  # max 3 concurrent Kling calls

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)
                if not listing:
                    raise ValueError(f"Listing {listing_id} not found")

                # Get package selections with asset + vision data
                selections = (await session.execute(
                    select(PackageSelection, Asset, VisionResult)
                    .join(Asset, PackageSelection.asset_id == Asset.id)
                    .outerjoin(VisionResult, (VisionResult.asset_id == Asset.id) & (VisionResult.tier == 1))
                    .where(PackageSelection.listing_id == listing_id)
                    .order_by(PackageSelection.position)
                )).all()

                if not selections:
                    return {"skipped": True, "reason": "No package selections"}

                # Select photos for video using slot priority
                selected = self._select_photos(selections)
                if not selected:
                    return {"skipped": True, "reason": "No photos above score floor"}

                # Generate clips via Kling
                clip_urls = await self._generate_clips(selected, listing.metadata_)

                # Filter out failed clips
                successful = [(s, url) for s, url in zip(selected, clip_urls) if url]
                if not successful:
                    return {"status": "failed", "reason": "All clips failed to generate"}

                # Download clips to temp files
                clip_paths = await self._download_clips([url for _, url in successful])

                # Stitch into final video
                transitions = [get_transition(i, len(successful)) for i in range(len(successful))]
                video_bytes = self._stitcher.stitch(clip_paths, transitions)

                # Upload to S3
                s3_key = self._storage.upload_bytes(
                    data=video_bytes,
                    key=f"videos/{listing_id}/tour.mp4",
                    content_type="video/mp4",
                )

                # Create VideoAsset record
                video_asset = VideoAsset(
                    tenant_id=listing.tenant_id,
                    listing_id=listing_id,
                    s3_key=s3_key,
                    video_type="ai_generated",
                    duration_seconds=len(successful) * settings.video_clip_duration,
                    status="ready",
                    clip_count=len(successful),
                )
                session.add(video_asset)

                await emit_event(
                    session=session,
                    event_type="video.completed",
                    payload={
                        "listing_id": str(listing_id),
                        "video_type": "ai_generated",
                        "clip_count": len(successful),
                        "s3_key": s3_key,
                    },
                    tenant_id=str(context.tenant_id),
                    listing_id=str(listing_id),
                )

                # Clean up temp files
                for p in clip_paths:
                    try:
                        os.unlink(p)
                    except OSError:
                        pass

        return {
            "status": "ready",
            "clip_count": len(successful),
            "video_asset_id": str(video_asset.id),
            "s3_key": s3_key,
        }

    def _select_photos(self, selections) -> list[tuple]:
        """Select up to max_photos using slot priority order."""
        # Build lookup: room_label → best (selection, asset, vision_result)
        by_room: dict[str, tuple] = {}
        for ps, asset, vr in selections:
            room = vr.room_label if vr else "unknown"
            score = vr.quality_score / 100.0 if vr else 0
            # Keep highest-scored per room
            if room not in by_room or score > (by_room[room][2].quality_score / 100.0 if by_room[room][2] else 0):
                by_room[room] = (ps, asset, vr)

        # Select in slot order
        selected = []
        for room in SLOT_ORDER:
            if room in by_room and len(selected) < self._max_photos:
                _, asset, vr = by_room[room]
                score = vr.quality_score / 100.0 if vr else 0
                # Drone and exterior bypass score floor
                if room in ("drone", "exterior") or score >= self._score_floor:
                    selected.append(by_room[room])
        return selected

    async def _generate_clips(self, selected, metadata) -> list[str | None]:
        """Generate Kling clips concurrently with rate limiting."""
        async def generate_one(index, ps, asset, vr):
            room = vr.room_label if vr else "living_room"
            prompt = get_prompt_for_room(room, metadata)
            camera = get_camera_control(room)

            async with self._semaphore:
                if index > 0:
                    await asyncio.sleep(3)  # Stagger to avoid rate limits
                try:
                    task_id = await self._kling.generate_clip(
                        image_url=asset.file_path,
                        prompt=prompt,
                        negative_prompt=NEGATIVE_PROMPT,
                        camera_control=camera,
                    )
                    url = await self._kling.poll_task(task_id)
                    return url
                except Exception:
                    return None

        tasks = [generate_one(i, ps, asset, vr) for i, (ps, asset, vr) in enumerate(selected)]
        return await asyncio.gather(*tasks)

    async def _download_clips(self, urls: list[str]) -> list[str]:
        """Download clip URLs to temporary files."""
        paths = []
        async with httpx.AsyncClient(timeout=60) as client:
            for i, url in enumerate(urls):
                resp = await client.get(url)
                path = os.path.join(tempfile.gettempdir(), f"launchlens_clip_{i}.mp4")
                with open(path, "wb") as f:
                    f.write(resp.content)
                paths.append(path)
        return paths
```

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_video.py -v 2>&1 | tail -20
```

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/agents/video.py src/launchlens/services/video_stitcher.py tests/test_agents/test_video.py && git commit -m "feat: add VideoAgent with Kling pipeline and FFmpeg stitching"
```

---

### Task 4: ChapterAgent (auto-chapters for pro videos)

**Files:**
- Create: `src/launchlens/agents/chapter.py`
- Create: `tests/test_agents/test_chapter.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_agents/test_chapter.py`:

```python
# tests/test_agents/test_chapter.py
import uuid
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import select
from tests.test_agents.conftest import make_session_factory
from launchlens.agents.base import AgentContext
from launchlens.agents.chapter import ChapterAgent
from launchlens.models.video_asset import VideoAsset
from launchlens.models.listing import Listing, ListingState

MOCK_CHAPTER_RESPONSE = json.dumps({
    "chapters": [
        {"time": 0, "label": "exterior", "description": "Front entrance and curb appeal"},
        {"time": 12, "label": "living_room", "description": "Open-concept living area"},
        {"time": 25, "label": "kitchen", "description": "Modern kitchen with island"},
        {"time": 38, "label": "primary_bedroom", "description": "Spacious primary suite"},
        {"time": 50, "label": "backyard", "description": "Private backyard with patio"},
    ]
})


@pytest.fixture
async def listing_with_pro_video(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "500 Pro Video Dr"}, metadata_={},
        state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    video = VideoAsset(
        tenant_id=tenant_id, listing_id=listing.id,
        s3_key=f"videos/{listing.id}/pro-tour.mp4",
        video_type="professional", duration_seconds=60,
        status="ready",
    )
    db_session.add(video)
    await db_session.flush()
    return listing, video


@pytest.mark.asyncio
async def test_chapter_agent_adds_chapters(db_session, listing_with_pro_video):
    listing, video = listing_with_pro_video
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_vision = MagicMock()
    mock_vision.analyze_with_prompt = AsyncMock(return_value=MOCK_CHAPTER_RESPONSE)

    agent = ChapterAgent(
        vision_provider=mock_vision,
        session_factory=make_session_factory(db_session),
    )
    result = await agent.execute(ctx)

    assert result["chapter_count"] == 5

    await db_session.refresh(video)
    assert video.chapters is not None
    assert len(video.chapters) == 5
    assert video.chapters[0]["label"] == "exterior"


@pytest.mark.asyncio
async def test_chapter_agent_skips_when_no_video(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id, address={"street": "No Video St"}, metadata_={},
        state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    agent = ChapterAgent(
        vision_provider=MagicMock(),
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)
    assert result.get("skipped") is True
```

- [ ] **Step 2: Implement ChapterAgent**

Create `src/launchlens/agents/chapter.py`:

```python
"""ChapterAgent — analyzes video keyframes via GPT-4V to generate chapter markers."""

import uuid
import json
from sqlalchemy import select

from launchlens.database import AsyncSessionLocal
from launchlens.models.listing import Listing
from launchlens.models.video_asset import VideoAsset
from launchlens.providers import get_vision_provider
from launchlens.services.events import emit_event
from .base import BaseAgent, AgentContext

CHAPTER_EXTRACTION_PROMPT = """\
Analyze this real estate property tour video. Identify the key scene transitions and room changes.

For each distinct scene/room, provide:
- "time": approximate timestamp in seconds where the scene starts
- "label": room type (use: exterior, living_room, kitchen, bedroom, primary_bedroom, bathroom, primary_bathroom, dining_room, office, garage, pool, backyard, entryway, basement)
- "description": one-line description of what's shown

Return ONLY valid JSON:
{
  "chapters": [
    {"time": 0, "label": "exterior", "description": "Front entrance and curb appeal"},
    ...
  ]
}
"""


class ChapterAgent(BaseAgent):
    agent_name = "chapter"

    def __init__(self, vision_provider=None, session_factory=None):
        self._vision_provider = vision_provider or get_vision_provider()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)
                if not listing:
                    raise ValueError(f"Listing {listing_id} not found")

                # Find the latest video for this listing (prefer professional, then ai_generated)
                video = (await session.execute(
                    select(VideoAsset)
                    .where(VideoAsset.listing_id == listing_id, VideoAsset.status == "ready")
                    .order_by(
                        # professional first, then by most recent
                        VideoAsset.video_type.desc(),
                        VideoAsset.created_at.desc(),
                    )
                    .limit(1)
                )).scalar_one_or_none()

                if not video:
                    return {"skipped": True, "reason": "No ready video found"}

                # For AI-generated videos, chapters are derived from clip order (already known)
                # For professional videos, use GPT-4V to analyze keyframes
                if video.video_type == "ai_generated" and video.chapters:
                    return {"skipped": True, "reason": "AI video already has chapters from clip metadata"}

                # Use GPT-4V to analyze the video thumbnail/keyframes
                # MVP: analyze the video S3 key as an image URL (thumbnail extraction is Phase 2)
                raw_response = await self._vision_provider.analyze_with_prompt(
                    image_url=video.thumbnail_s3_key or video.s3_key,
                    prompt=CHAPTER_EXTRACTION_PROMPT,
                )

                try:
                    parsed = json.loads(raw_response)
                    chapters = parsed.get("chapters", [])
                except (json.JSONDecodeError, AttributeError):
                    chapters = []

                video.chapters = chapters

                await emit_event(
                    session=session,
                    event_type="chapter.completed",
                    payload={
                        "listing_id": str(listing_id),
                        "video_asset_id": str(video.id),
                        "chapter_count": len(chapters),
                    },
                    tenant_id=str(context.tenant_id),
                    listing_id=str(listing_id),
                )

        return {"chapter_count": len(chapters), "video_asset_id": str(video.id)}
```

- [ ] **Step 3: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_chapter.py -v 2>&1 | tail -15
```

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/agents/chapter.py tests/test_agents/test_chapter.py && git commit -m "feat: add ChapterAgent (GPT-4V auto-chapter markers for videos)"
```

---

### Task 5: SocialCutAgent (platform-specific clips)

**Files:**
- Create: `src/launchlens/agents/social_cuts.py`
- Create: `tests/test_agents/test_social_cuts.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_agents/test_social_cuts.py`:

```python
# tests/test_agents/test_social_cuts.py
import uuid
import pytest
from unittest.mock import MagicMock
from sqlalchemy import select
from tests.test_agents.conftest import make_session_factory
from launchlens.agents.base import AgentContext
from launchlens.agents.social_cuts import SocialCutAgent, PLATFORM_SPECS
from launchlens.models.video_asset import VideoAsset
from launchlens.models.listing import Listing, ListingState


def test_platform_specs_exist():
    assert "instagram" in PLATFORM_SPECS
    assert "tiktok" in PLATFORM_SPECS
    assert "facebook" in PLATFORM_SPECS
    assert "youtube_short" in PLATFORM_SPECS
    assert PLATFORM_SPECS["instagram"]["width"] == 1080
    assert PLATFORM_SPECS["instagram"]["height"] == 1920


@pytest.fixture
async def listing_with_video(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "600 Social Cut Dr"}, metadata_={},
        state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    video = VideoAsset(
        tenant_id=tenant_id, listing_id=listing.id,
        s3_key=f"videos/{listing.id}/tour.mp4",
        video_type="ai_generated", duration_seconds=40, status="ready",
    )
    db_session.add(video)
    await db_session.flush()
    return listing, video


@pytest.mark.asyncio
async def test_social_cut_agent_creates_cuts(db_session, listing_with_video):
    listing, video = listing_with_video
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_storage = MagicMock()
    mock_storage.upload_bytes = MagicMock(side_effect=lambda data, key, content_type: key)

    mock_cutter = MagicMock()
    mock_cutter.create_cut = MagicMock(return_value=b"fake-cut-bytes")

    agent = SocialCutAgent(
        storage_service=mock_storage,
        video_cutter=mock_cutter,
        session_factory=make_session_factory(db_session),
    )
    result = await agent.execute(ctx)

    assert result["cut_count"] == 4  # instagram, tiktok, facebook, youtube_short

    await db_session.refresh(video)
    assert video.social_cuts is not None
    assert len(video.social_cuts) == 4
    platforms = [c["platform"] for c in video.social_cuts]
    assert "instagram" in platforms
    assert "facebook" in platforms


@pytest.mark.asyncio
async def test_social_cut_agent_skips_no_video(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id, address={"street": "No Cut St"}, metadata_={},
        state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    agent = SocialCutAgent(
        storage_service=MagicMock(), video_cutter=MagicMock(),
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)
    assert result.get("skipped") is True
```

- [ ] **Step 2: Implement SocialCutAgent**

Create `src/launchlens/agents/social_cuts.py`:

```python
"""SocialCutAgent — creates platform-specific video clips from a property tour video."""

import uuid
from sqlalchemy import select

from launchlens.database import AsyncSessionLocal
from launchlens.models.listing import Listing
from launchlens.models.video_asset import VideoAsset
from launchlens.services.storage import StorageService
from launchlens.services.events import emit_event
from .base import BaseAgent, AgentContext

PLATFORM_SPECS: dict[str, dict] = {
    "instagram": {
        "width": 1080, "height": 1920,  # 9:16 vertical
        "max_duration": 30,
        "format": "mp4",
    },
    "tiktok": {
        "width": 1080, "height": 1920,  # 9:16 vertical
        "max_duration": 60,
        "format": "mp4",
    },
    "facebook": {
        "width": 1920, "height": 1080,  # 16:9 horizontal
        "max_duration": 60,
        "format": "mp4",
    },
    "youtube_short": {
        "width": 1080, "height": 1920,  # 9:16 vertical
        "max_duration": 60,
        "format": "mp4",
    },
}


class VideoCutter:
    """FFmpeg-based video cropper/resizer for social platforms."""

    def create_cut(
        self,
        source_bytes: bytes,
        width: int,
        height: int,
        max_duration: int,
    ) -> bytes:
        """Crop/resize a video for a specific platform. Returns video bytes.
        MVP: returns the source bytes truncated (actual FFmpeg cropping in Phase 2).
        """
        # MVP: return source as-is. Phase 2 adds actual FFmpeg crop + resize.
        return source_bytes


class SocialCutAgent(BaseAgent):
    agent_name = "social_cuts"

    def __init__(self, storage_service=None, video_cutter=None, session_factory=None):
        self._storage = storage_service or StorageService()
        self._cutter = video_cutter or VideoCutter()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)
                if not listing:
                    raise ValueError(f"Listing {listing_id} not found")

                video = (await session.execute(
                    select(VideoAsset)
                    .where(VideoAsset.listing_id == listing_id, VideoAsset.status == "ready")
                    .order_by(VideoAsset.created_at.desc())
                    .limit(1)
                )).scalar_one_or_none()

                if not video:
                    return {"skipped": True, "reason": "No ready video found"}

                # Generate a cut for each platform
                cuts = []
                for platform, spec in PLATFORM_SPECS.items():
                    cut_bytes = self._cutter.create_cut(
                        source_bytes=b"placeholder",  # MVP: actual download in Phase 2
                        width=spec["width"],
                        height=spec["height"],
                        max_duration=spec["max_duration"],
                    )

                    s3_key = self._storage.upload_bytes(
                        data=cut_bytes,
                        key=f"videos/{listing_id}/social/{platform}.mp4",
                        content_type="video/mp4",
                    )

                    cuts.append({
                        "platform": platform,
                        "s3_key": s3_key,
                        "width": spec["width"],
                        "height": spec["height"],
                        "max_duration": spec["max_duration"],
                    })

                video.social_cuts = cuts

                await emit_event(
                    session=session,
                    event_type="social_cuts.completed",
                    payload={
                        "listing_id": str(listing_id),
                        "video_asset_id": str(video.id),
                        "cut_count": len(cuts),
                        "platforms": [c["platform"] for c in cuts],
                    },
                    tenant_id=str(context.tenant_id),
                    listing_id=str(listing_id),
                )

        return {"cut_count": len(cuts), "video_asset_id": str(video.id)}
```

- [ ] **Step 3: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_social_cuts.py -v 2>&1 | tail -15
```

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/agents/social_cuts.py tests/test_agents/test_social_cuts.py && git commit -m "feat: add SocialCutAgent (platform-specific video clips)"
```

---

### Task 6: Video API endpoints

**Files:**
- Modify: `src/launchlens/api/listings.py`
- Create: `tests/test_api/test_video.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_api/test_video.py`:

```python
# tests/test_api/test_video.py
import uuid
import pytest
import jwt as pyjwt
from httpx import AsyncClient
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
async def test_get_video_not_ready(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "No Video St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]
    resp = await async_client.get(f"/listings/{listing_id}/video", headers=_auth(token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_social_cuts_not_ready(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "No Cuts St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]
    resp = await async_client.get(f"/listings/{listing_id}/video/social-cuts", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_video_upload_endpoint_exists(async_client: AsyncClient):
    """POST /listings/{id}/video/upload should exist (even if it returns 404 for missing listing)."""
    token, _ = await _register(async_client)
    resp = await async_client.post(
        f"/listings/{uuid.uuid4()}/video/upload",
        json={"s3_key": "videos/test.mp4", "video_type": "professional"},
        headers=_auth(token),
    )
    assert resp.status_code == 404  # listing not found, but route exists


@pytest.mark.asyncio
async def test_video_requires_auth(async_client: AsyncClient):
    resp = await async_client.get(f"/listings/{uuid.uuid4()}/video")
    assert resp.status_code == 401
```

- [ ] **Step 2: Add video endpoints to listings router**

Read `src/launchlens/api/listings.py` first. Add these imports and endpoints:

```python
from launchlens.models.video_asset import VideoAsset


@router.get("/{listing_id}/video")
async def get_video(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = (await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == current_user.tenant_id)
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    video = (await db.execute(
        select(VideoAsset)
        .where(VideoAsset.listing_id == listing.id, VideoAsset.status == "ready")
        .order_by(VideoAsset.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="No video available")

    return {
        "s3_key": video.s3_key,
        "video_type": video.video_type,
        "duration_seconds": video.duration_seconds,
        "status": video.status,
        "chapters": video.chapters,
        "social_cuts": video.social_cuts,
        "thumbnail_s3_key": video.thumbnail_s3_key,
        "clip_count": video.clip_count,
        "created_at": video.created_at.isoformat(),
    }


@router.get("/{listing_id}/video/social-cuts")
async def get_video_social_cuts(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = (await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == current_user.tenant_id)
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    video = (await db.execute(
        select(VideoAsset)
        .where(VideoAsset.listing_id == listing.id, VideoAsset.status == "ready")
        .order_by(VideoAsset.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    if not video or not video.social_cuts:
        return []
    return video.social_cuts


@router.post("/{listing_id}/video/upload", status_code=201)
async def upload_video(
    listing_id: uuid.UUID,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a user-submitted or professional video."""
    listing = (await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == current_user.tenant_id)
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    video_type = body.get("video_type", "user_raw")
    if video_type not in ("user_raw", "professional"):
        raise HTTPException(status_code=400, detail="video_type must be 'user_raw' or 'professional'")

    video = VideoAsset(
        tenant_id=current_user.tenant_id,
        listing_id=listing.id,
        s3_key=body["s3_key"],
        video_type=video_type,
        duration_seconds=body.get("duration_seconds"),
        status="ready",
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    return {
        "id": str(video.id),
        "s3_key": video.s3_key,
        "video_type": video.video_type,
        "status": video.status,
    }
```

- [ ] **Step 3: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_video.py -v 2>&1 | tail -15
```

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/api/listings.py tests/test_api/test_video.py && git commit -m "feat: add video API endpoints (get, social-cuts, upload)"
```

---

### Task 7: Wire into pipeline + tag

**Files:**
- Modify: `src/launchlens/activities/pipeline.py`
- Modify: `src/launchlens/workflows/listing_pipeline.py`

- [ ] **Step 1: Add video activities**

In `src/launchlens/activities/pipeline.py`, add:

```python
@activity.defn
async def run_video(context: AgentContext) -> dict:
    from launchlens.agents.video import VideoAgent
    return await VideoAgent().execute(context)


@activity.defn
async def run_chapters(context: AgentContext) -> dict:
    from launchlens.agents.chapter import ChapterAgent
    return await ChapterAgent().execute(context)


@activity.defn
async def run_social_cuts(context: AgentContext) -> dict:
    from launchlens.agents.social_cuts import SocialCutAgent
    return await SocialCutAgent().execute(context)
```

Add all three to `ALL_ACTIVITIES`.

- [ ] **Step 2: Wire into workflow**

Read `src/launchlens/workflows/listing_pipeline.py` first. Add imports for `run_video`, `run_chapters`, `run_social_cuts` in the `imports_passed_through` block.

The VideoAgent runs in **parallel with human review** — start it before the wait, collect result after:

```python
        # Start video generation in parallel with human review
        video_task = workflow.execute_activity(
            run_video, ctx,
            start_to_close_timeout=timedelta(minutes=30),  # Kling generation takes time
            retry_policy=_DEFAULT_RETRY,
        )

        # Wait for human review
        await workflow.wait_condition(lambda: self._review_completed)

        # Collect video result (may already be done)
        video_result = await video_task

        # Phase 2: Post-approval pipeline
        await workflow.execute_activity(run_content, ctx, ...)
        await workflow.execute_activity(run_brand, ctx, ...)
        await workflow.execute_activity(run_social_content, ctx, ...)

        # Video post-processing (chapters + social cuts)
        await workflow.execute_activity(
            run_chapters, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        await workflow.execute_activity(
            run_social_cuts, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )

        await workflow.execute_activity(run_mls_export, ctx, ...)
        await workflow.execute_activity(run_distribution, ctx, ...)
```

- [ ] **Step 3: Run full test suite**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest --tb=short -q 2>&1 | tail -5
```

- [ ] **Step 4: Commit and tag**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/activities/pipeline.py src/launchlens/workflows/listing_pipeline.py && git commit -m "feat: wire video pipeline into Temporal workflow (parallel with review)" && git tag v0.9.2-video-pipeline && echo "Tagged v0.9.2-video-pipeline"
```

---

## NOT in scope

- Virtual drone flyover from ground-level photos (tech doesn't exist reliably)
- Virtual staging video (Phase 3+)
- HLS transcoding + CDN streaming (Phase 2 — use S3 presigned URLs for MVP)
- Branded video player embed code (frontend feature)
- Video analytics (views, watch time) — Phase 2
- Copyright/music detection on uploaded videos — Phase 2
- Actual FFmpeg cropping in SocialCutAgent (MVP returns placeholder; Phase 2 adds real crop)
- Thumbnail extraction from video (Phase 2 — FFmpeg can do this)
- Multiple music tracks / music selection UI

## What already exists

- Kling AI integration in Juke Marketing Engine (production-tested)
- 16 room-specific cinematic prompts + camera controls
- FFmpeg stitching with xfade transitions + music overlay
- PackageSelection with scored + ordered photos per listing
- VisionResult with room_label for prompt selection
- `analyze_with_prompt` on VisionProvider (for ChapterAgent)
- StorageService with `upload_bytes` (for S3 uploads)
- Temporal workflow with Phase 1/Phase 2 and signal-based review gate
