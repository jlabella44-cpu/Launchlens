# FloorplanAgent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a FloorplanAgent that uses GPT-4V to parse a 2D floorplan image into room polygons, then generates a 3D dollhouse scene definition that the frontend can render with React Three Fiber — giving every listing an interactive 3D walkthrough.

**Architecture:** The agent takes a floorplan Asset (tagged `asset_type=floorplan`), sends it to GPT-4V with a structured extraction prompt, gets back room polygons as JSON (walls, rooms with labels and dimensions), matches rooms to VisionAgent's room labels, and stores a `DollhouseScene` record with the full scene JSON. A new API endpoint `GET /listings/{id}/dollhouse` returns the scene data. The frontend renders it as an isometric 3D view with clickable rooms that show the best photo for each room.

**Tech Stack:** GPT-4V (via OpenAIVisionProvider), SQLAlchemy 2.0 async, Three.js/React Three Fiber (frontend rendering — deferred to frontend plan), pytest-asyncio

---

## File Structure

```
src/launchlens/
  agents/
    floorplan.py               CREATE  — FloorplanAgent (GPT-4V floorplan parsing → scene JSON)
  models/
    dollhouse_scene.py         CREATE  — DollhouseScene model (listing_id, scene_json, room_count)
  api/
    listings.py                MODIFY  — add GET /listings/{id}/dollhouse

alembic/versions/
  006_dollhouse_scenes.py      CREATE  — new table

tests/test_agents/
  test_floorplan.py            CREATE  — agent tests
tests/test_api/
  test_dollhouse.py            CREATE  — endpoint test
```

---

## Key Design Decisions

### Floorplan detection
An uploaded asset is identified as a floorplan by file naming convention (`*floorplan*`, `*floor-plan*`, `*floor_plan*`) or by explicit `asset_type` tag. For MVP, the agent checks file_path for "floorplan" in the name. Phase 2 can add GPT-4V classification ("Is this image a floorplan or a photo?").

### GPT-4V structured extraction prompt
The prompt asks GPT-4V to return a specific JSON schema:

```json
{
  "rooms": [
    {
      "label": "kitchen",
      "polygon": [[0, 0], [4, 0], [4, 3], [0, 3]],
      "width_meters": 4.0,
      "height_meters": 3.0,
      "doors": [{"wall": "south", "position": 0.5}],
      "windows": [{"wall": "east", "position": 0.3}]
    }
  ],
  "overall_width_meters": 12.0,
  "overall_height_meters": 8.0
}
```

Polygon coordinates are normalized (0-1 range relative to overall dimensions), so the frontend can scale to any render size.

### Room-to-photo matching
The agent matches `rooms[].label` to `VisionResult.room_label` for the same listing. Each room gets a `best_photo_asset_id` — the highest-scored photo for that room type.

### Scene JSON format (for Three.js rendering)
The final `scene_json` stored in DollhouseScene includes everything the frontend needs:

```json
{
  "version": 1,
  "dimensions": {"width": 12.0, "height": 8.0},
  "wall_height": 2.7,
  "rooms": [
    {
      "label": "kitchen",
      "polygon": [[0, 0], [4, 0], [4, 3], [0, 3]],
      "color": "#FEF3C7",
      "best_photo_asset_id": "uuid-of-best-kitchen-photo",
      "photo_score": 0.92
    }
  ]
}
```

### Frontend rendering (deferred to frontend plan)
The scene JSON is consumed by a `<DollhouseViewer>` React Three Fiber component:
- Each room polygon → extruded 3D shape (floor + walls)
- Room color based on type (kitchen=warm, bathroom=cool, etc.)
- Click room → modal shows the best photo
- Isometric camera angle (top-down at 45 degrees)
- Orbit controls for rotation

---

## Tasks

---

### Task 1: DollhouseScene model + migration

**Files:**
- Create: `src/launchlens/models/dollhouse_scene.py`
- Create: `alembic/versions/006_dollhouse_scenes.py`
- Create: `tests/test_agents/test_floorplan.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_agents/test_floorplan.py`:

```python
# tests/test_agents/test_floorplan.py
import pytest


def test_dollhouse_scene_model_exists():
    from launchlens.models.dollhouse_scene import DollhouseScene
    assert hasattr(DollhouseScene, "listing_id")
    assert hasattr(DollhouseScene, "scene_json")
    assert hasattr(DollhouseScene, "room_count")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_floorplan.py -v 2>&1 | tail -10
```

- [ ] **Step 3: Create DollhouseScene model**

Create `src/launchlens/models/dollhouse_scene.py`:

```python
import uuid
from sqlalchemy import UUID, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base import TenantScopedModel


class DollhouseScene(TenantScopedModel):
    __tablename__ = "dollhouse_scenes"
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    scene_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    room_count: Mapped[int] = mapped_column(Integer, default=0)
    floorplan_asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
```

- [ ] **Step 4: Create migration**

Create `alembic/versions/006_dollhouse_scenes.py`:

```python
"""dollhouse scenes

Revision ID: 006
Revises: 005
Create Date: 2026-03-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dollhouse_scenes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("scene_json", postgresql.JSONB, nullable=False),
        sa.Column("room_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("floorplan_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.execute("ALTER TABLE dollhouse_scenes ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON dollhouse_scenes
        USING (tenant_id = current_setting('app.current_tenant')::uuid)
    """)


def downgrade() -> None:
    op.drop_table("dollhouse_scenes")
```

- [ ] **Step 5: Run test**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_floorplan.py -v 2>&1 | tail -10
```

- [ ] **Step 6: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/models/dollhouse_scene.py alembic/versions/006_dollhouse_scenes.py tests/test_agents/test_floorplan.py && git commit -m "feat: add DollhouseScene model and migration"
```

---

### Task 2: FloorplanAgent (GPT-4V parsing + scene generation)

**Files:**
- Create: `src/launchlens/agents/floorplan.py`
- Modify: `tests/test_agents/test_floorplan.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_agents/test_floorplan.py`:

```python
import uuid
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import select
from tests.test_agents.conftest import make_session_factory
from launchlens.agents.base import AgentContext
from launchlens.agents.floorplan import FloorplanAgent, FLOORPLAN_EXTRACTION_PROMPT
from launchlens.models.dollhouse_scene import DollhouseScene
from launchlens.models.listing import Listing, ListingState
from launchlens.models.asset import Asset
from launchlens.models.vision_result import VisionResult


MOCK_GPT4V_RESPONSE = json.dumps({
    "rooms": [
        {
            "label": "living_room",
            "polygon": [[0.0, 0.0], [0.5, 0.0], [0.5, 0.4], [0.0, 0.4]],
            "width_meters": 6.0,
            "height_meters": 4.5,
            "doors": [{"wall": "south", "position": 0.5}],
            "windows": [{"wall": "east", "position": 0.3}],
        },
        {
            "label": "kitchen",
            "polygon": [[0.5, 0.0], [1.0, 0.0], [1.0, 0.4], [0.5, 0.4]],
            "width_meters": 5.0,
            "height_meters": 4.5,
            "doors": [{"wall": "west", "position": 0.5}],
            "windows": [],
        },
        {
            "label": "bedroom",
            "polygon": [[0.0, 0.4], [0.5, 0.4], [0.5, 1.0], [0.0, 1.0]],
            "width_meters": 6.0,
            "height_meters": 5.0,
            "doors": [{"wall": "north", "position": 0.3}],
            "windows": [{"wall": "west", "position": 0.5}],
        },
    ],
    "overall_width_meters": 12.0,
    "overall_height_meters": 9.0,
})


@pytest.fixture
async def listing_with_floorplan(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "300 Dollhouse Dr", "city": "Austin", "state": "TX"},
        metadata_={"beds": 2, "baths": 1, "sqft": 1200, "price": 300000},
        state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    # Regular photos
    photo_rooms = ["living_room", "kitchen", "bedroom"]
    photos = []
    for i, room in enumerate(photo_rooms):
        a = Asset(
            tenant_id=tenant_id, listing_id=listing.id,
            file_path=f"listings/{listing.id}/{room}.jpg", file_hash=f"photo{i}", state="ingested",
        )
        db_session.add(a)
        photos.append(a)
    await db_session.flush()

    # Vision results for photos
    for i, (a, room) in enumerate(zip(photos, photo_rooms)):
        vr = VisionResult(
            tenant_id=tenant_id, asset_id=a.id,
            tier=1, room_label=room,
            quality_score=90 - i * 5, commercial_score=80, hero_candidate=(i == 0),
        )
        db_session.add(vr)

    # Floorplan asset
    floorplan = Asset(
        tenant_id=tenant_id, listing_id=listing.id,
        file_path=f"listings/{listing.id}/floorplan.jpg", file_hash="fp001", state="ingested",
    )
    db_session.add(floorplan)
    await db_session.flush()

    return listing, floorplan, photos


@pytest.mark.asyncio
async def test_floorplan_agent_creates_scene(db_session, listing_with_floorplan):
    listing, floorplan, photos = listing_with_floorplan
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_vision = MagicMock()
    mock_vision.analyze_with_prompt = AsyncMock(return_value=MOCK_GPT4V_RESPONSE)

    agent = FloorplanAgent(
        vision_provider=mock_vision,
        session_factory=make_session_factory(db_session),
    )
    result = await agent.execute(ctx)

    assert result["room_count"] == 3
    assert "scene_id" in result

    scenes = (await db_session.execute(select(DollhouseScene))).scalars().all()
    assert len(scenes) == 1
    scene = scenes[0]
    assert scene.listing_id == listing.id
    assert scene.room_count == 3
    assert len(scene.scene_json["rooms"]) == 3


@pytest.mark.asyncio
async def test_floorplan_agent_matches_photos_to_rooms(db_session, listing_with_floorplan):
    listing, floorplan, photos = listing_with_floorplan
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_vision = MagicMock()
    mock_vision.analyze_with_prompt = AsyncMock(return_value=MOCK_GPT4V_RESPONSE)

    agent = FloorplanAgent(
        vision_provider=mock_vision,
        session_factory=make_session_factory(db_session),
    )
    result = await agent.execute(ctx)

    scenes = (await db_session.execute(select(DollhouseScene))).scalars().all()
    scene = scenes[0]

    # Each room should have a best_photo_asset_id matched from vision results
    rooms_with_photos = [r for r in scene.scene_json["rooms"] if r.get("best_photo_asset_id")]
    assert len(rooms_with_photos) == 3  # all 3 rooms have matching photos


@pytest.mark.asyncio
async def test_floorplan_agent_emits_event(db_session, listing_with_floorplan):
    listing, floorplan, photos = listing_with_floorplan
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_vision = MagicMock()
    mock_vision.analyze_with_prompt = AsyncMock(return_value=MOCK_GPT4V_RESPONSE)

    agent = FloorplanAgent(
        vision_provider=mock_vision,
        session_factory=make_session_factory(db_session),
    )
    await agent.execute(ctx)

    from launchlens.models.event import Event
    events = (await db_session.execute(
        select(Event).where(Event.event_type == "floorplan.completed")
    )).scalars().all()
    assert len(events) == 1


@pytest.mark.asyncio
async def test_floorplan_agent_no_floorplan_skips(db_session):
    """When no floorplan asset exists, agent returns gracefully."""
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "No Floor St"}, metadata_={}, state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    mock_vision = MagicMock()
    agent = FloorplanAgent(
        vision_provider=mock_vision,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result["room_count"] == 0
    assert result.get("skipped") is True
    mock_vision.analyze_with_prompt.assert_not_called()


def test_extraction_prompt_exists():
    """The structured extraction prompt must be defined."""
    assert "rooms" in FLOORPLAN_EXTRACTION_PROMPT
    assert "polygon" in FLOORPLAN_EXTRACTION_PROMPT
    assert "JSON" in FLOORPLAN_EXTRACTION_PROMPT
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_floorplan.py -k "creates_scene or matches_photos or emits_event or skips or prompt" -v 2>&1 | tail -15
```

- [ ] **Step 3: Add analyze_with_prompt to vision provider base**

Read `src/launchlens/providers/base.py` first. The `VisionProvider` ABC has `analyze(image_url)`. Add a new method for structured prompts:

```python
# In VisionProvider ABC:
async def analyze_with_prompt(self, image_url: str, prompt: str) -> str:
    """Send an image with a custom prompt. Returns raw text response."""
    raise NotImplementedError
```

Also add it to `MockVisionProvider` in `src/launchlens/providers/mock.py`:

```python
async def analyze_with_prompt(self, image_url: str, prompt: str) -> str:
    return "{}"
```

And to `OpenAIVisionProvider` in `src/launchlens/providers/openai_vision.py` (this is the GPT-4V provider):

```python
async def analyze_with_prompt(self, image_url: str, prompt: str) -> str:
    """Send image + custom prompt to GPT-4V, return raw text."""
    response = await self._client.chat.completions.create(
        model=self._model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
        max_tokens=2000,
    )
    return response.choices[0].message.content
```

- [ ] **Step 4: Implement FloorplanAgent**

Create `src/launchlens/agents/floorplan.py`:

```python
import uuid
import json
from sqlalchemy import select

from launchlens.database import AsyncSessionLocal
from launchlens.models.listing import Listing
from launchlens.models.asset import Asset
from launchlens.models.vision_result import VisionResult
from launchlens.models.dollhouse_scene import DollhouseScene
from launchlens.providers import get_vision_provider
from launchlens.services.events import emit_event
from .base import BaseAgent, AgentContext

# Room colors for 3D rendering
ROOM_COLORS = {
    "living_room": "#FEF3C7",
    "kitchen": "#DBEAFE",
    "bedroom": "#E0E7FF",
    "bathroom": "#D1FAE5",
    "dining_room": "#FDE68A",
    "exterior": "#D1D5DB",
    "office": "#EDE9FE",
    "garage": "#E5E7EB",
    "pool": "#BFDBFE",
    "backyard": "#BBF7D0",
}

FLOORPLAN_EXTRACTION_PROMPT = """\
Analyze this floorplan image and extract the room layout as structured JSON.

For each room you can identify, provide:
- "label": room type (use one of: living_room, kitchen, bedroom, bathroom, dining_room, office, garage, exterior)
- "polygon": array of [x, y] coordinates defining the room boundary, normalized to 0.0-1.0 range relative to the overall floorplan dimensions
- "width_meters": estimated width in meters
- "height_meters": estimated height in meters
- "doors": array of {"wall": "north|south|east|west", "position": 0.0-1.0 along that wall}
- "windows": array of {"wall": "north|south|east|west", "position": 0.0-1.0 along that wall}

Also provide:
- "overall_width_meters": total floorplan width
- "overall_height_meters": total floorplan height

Return ONLY valid JSON with this structure:
{
  "rooms": [...],
  "overall_width_meters": number,
  "overall_height_meters": number
}
"""


class FloorplanAgent(BaseAgent):
    agent_name = "floorplan"

    def __init__(self, vision_provider=None, session_factory=None):
        self._vision_provider = vision_provider or get_vision_provider()
        self._session_factory = session_factory or AsyncSessionLocal

    def _find_floorplan_asset(self, assets: list[Asset]) -> Asset | None:
        """Find the floorplan asset by filename convention."""
        for a in assets:
            path_lower = a.file_path.lower()
            if any(kw in path_lower for kw in ("floorplan", "floor-plan", "floor_plan", "fp_", "fp-")):
                return a
        return None

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)
                if not listing:
                    raise ValueError(f"Listing {listing_id} not found")

                # Find floorplan asset
                assets_result = await session.execute(
                    select(Asset).where(Asset.listing_id == listing_id)
                )
                all_assets = assets_result.scalars().all()
                floorplan_asset = self._find_floorplan_asset(all_assets)

                if not floorplan_asset:
                    return {"room_count": 0, "skipped": True, "reason": "No floorplan asset found"}

                # Extract room layout via GPT-4V
                raw_response = await self._vision_provider.analyze_with_prompt(
                    image_url=floorplan_asset.file_path,
                    prompt=FLOORPLAN_EXTRACTION_PROMPT,
                )

                try:
                    parsed = json.loads(raw_response)
                    rooms = parsed.get("rooms", [])
                except (json.JSONDecodeError, AttributeError):
                    return {"room_count": 0, "skipped": True, "reason": "Failed to parse GPT-4V response"}

                # Get vision results for photo matching
                vision_results = (await session.execute(
                    select(VisionResult).where(
                        VisionResult.asset_id.in_([a.id for a in all_assets]),
                        VisionResult.tier == 1,
                    ).order_by(VisionResult.quality_score.desc())
                )).scalars().all()

                # Group best photo per room label
                best_photo_by_room: dict[str, tuple[uuid.UUID, float]] = {}
                for vr in vision_results:
                    if vr.room_label and vr.room_label not in best_photo_by_room:
                        best_photo_by_room[vr.room_label] = (vr.asset_id, vr.quality_score)

                # Build scene JSON
                scene_rooms = []
                for room in rooms:
                    label = room.get("label", "unknown")
                    photo_info = best_photo_by_room.get(label)
                    scene_rooms.append({
                        "label": label,
                        "polygon": room.get("polygon", []),
                        "width_meters": room.get("width_meters", 0),
                        "height_meters": room.get("height_meters", 0),
                        "doors": room.get("doors", []),
                        "windows": room.get("windows", []),
                        "color": ROOM_COLORS.get(label, "#F3F4F6"),
                        "best_photo_asset_id": str(photo_info[0]) if photo_info else None,
                        "photo_score": photo_info[1] if photo_info else None,
                    })

                scene_json = {
                    "version": 1,
                    "dimensions": {
                        "width": parsed.get("overall_width_meters", 10),
                        "height": parsed.get("overall_height_meters", 8),
                    },
                    "wall_height": 2.7,
                    "rooms": scene_rooms,
                }

                scene = DollhouseScene(
                    tenant_id=listing.tenant_id,
                    listing_id=listing_id,
                    scene_json=scene_json,
                    room_count=len(scene_rooms),
                    floorplan_asset_id=floorplan_asset.id,
                )
                session.add(scene)

                await emit_event(
                    session=session,
                    event_type="floorplan.completed",
                    payload={
                        "listing_id": str(listing_id),
                        "room_count": len(scene_rooms),
                        "scene_id": str(scene.id) if hasattr(scene, 'id') else None,
                    },
                    tenant_id=str(context.tenant_id),
                    listing_id=str(listing_id),
                )

        return {
            "room_count": len(scene_rooms),
            "scene_id": str(scene.id),
        }
```

- [ ] **Step 5: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_floorplan.py -v 2>&1 | tail -20
```

- [ ] **Step 6: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/agents/floorplan.py src/launchlens/providers/base.py src/launchlens/providers/mock.py src/launchlens/providers/openai_vision.py tests/test_agents/test_floorplan.py && git commit -m "feat: add FloorplanAgent (GPT-4V floorplan parsing → 3D scene JSON)"
```

---

### Task 3: Dollhouse API endpoint + pipeline wiring + tag

**Files:**
- Modify: `src/launchlens/api/listings.py`
- Modify: `src/launchlens/activities/pipeline.py`
- Modify: `src/launchlens/workflows/listing_pipeline.py`
- Create: `tests/test_api/test_dollhouse.py`

- [ ] **Step 1: Write failing endpoint test**

Create `tests/test_api/test_dollhouse.py`:

```python
# tests/test_api/test_dollhouse.py
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
async def test_get_dollhouse_not_ready(async_client: AsyncClient):
    """GET /listings/{id}/dollhouse returns 404 when no scene exists."""
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "No Floor St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    resp = await async_client.get(f"/listings/{listing_id}/dollhouse", headers=_auth(token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_dollhouse_requires_auth(async_client: AsyncClient):
    resp = await async_client.get(f"/listings/{uuid.uuid4()}/dollhouse")
    assert resp.status_code == 401
```

- [ ] **Step 2: Add dollhouse endpoint**

In `src/launchlens/api/listings.py`, add:

```python
from launchlens.models.dollhouse_scene import DollhouseScene


@router.get("/{listing_id}/dollhouse")
async def get_dollhouse(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = (await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == current_user.tenant_id)
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    scene = (await db.execute(
        select(DollhouseScene)
        .where(DollhouseScene.listing_id == listing.id)
        .order_by(DollhouseScene.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Dollhouse not ready — upload a floorplan and run the pipeline")

    return {
        "scene_json": scene.scene_json,
        "room_count": scene.room_count,
        "created_at": scene.created_at.isoformat(),
    }
```

- [ ] **Step 3: Add activity + wire into pipeline**

In `src/launchlens/activities/pipeline.py`, add:

```python
@activity.defn
async def run_floorplan(context: AgentContext) -> dict:
    from launchlens.agents.floorplan import FloorplanAgent
    return await FloorplanAgent().execute(context)
```

Add to `ALL_ACTIVITIES`.

In `src/launchlens/workflows/listing_pipeline.py`, add `run_floorplan` import and call it in Phase 1 after `run_coverage` (before `run_packaging`):

```python
        await workflow.execute_activity(
            run_floorplan, ctx,
            start_to_close_timeout=_VISION_TIER2_TIMEOUT,  # GPT-4V call, needs longer timeout
            retry_policy=_DEFAULT_RETRY,
        )
```

This runs after coverage (so vision results exist for photo matching) but before packaging (so the dollhouse is ready when the user reviews).

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_dollhouse.py tests/test_agents/test_floorplan.py -v 2>&1 | tail -20
```

- [ ] **Step 5: Run full suite**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest --tb=short -q 2>&1 | tail -5
```

- [ ] **Step 6: Commit and tag**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/api/listings.py src/launchlens/activities/pipeline.py src/launchlens/workflows/listing_pipeline.py tests/test_api/test_dollhouse.py && git commit -m "feat: add dollhouse API endpoint and wire FloorplanAgent into pipeline" && git tag v0.9.1-floorplan-agent && echo "Tagged v0.9.1-floorplan-agent"
```

---

## NOT in scope

- Frontend 3D rendering component (`<DollhouseViewer>`) — deferred to frontend plan
- Image-based floorplan classification ("Is this a floorplan?") — MVP uses filename convention
- LiDAR room measurement integration — future
- Furniture placement in 3D scene — future
- Texture mapping (projecting photos onto walls) — future
- Multi-floor floorplan support — MVP handles single floor
- Floorplan image preprocessing (deskew, crop) — MVP sends raw image to GPT-4V
- Virtual staging integration — separate feature

## What already exists

- VisionResult with room_label, quality_score — used for photo-to-room matching
- Asset model with file_path — used to identify floorplan by filename
- OpenAIVisionProvider — GPT-4V integration (needs `analyze_with_prompt` method added)
- Agent pipeline with session injection + Outbox pattern
- Temporal workflow with Phase 1 / Phase 2 structure
- React Three Fiber in frontend plan (will render the scene JSON)
