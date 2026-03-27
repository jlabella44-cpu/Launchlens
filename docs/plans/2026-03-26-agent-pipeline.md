# Agent Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement all 8 agent classes so the LaunchLens pipeline runs end-to-end from photo upload to delivered listing package.

**Architecture:** Each agent extends `BaseAgent`, opens its own DB session via an injected `session_factory`, uses injected providers (defaulting to factory functions), transitions `Listing.state`, and emits domain events via the Outbox Pattern. VisionAgent runs two tiers: Google Vision (Tier 1, all assets) then GPT-4V (Tier 2, top-20 candidates). All agents are tested with mock providers and the Docker PostgreSQL test DB (port 5433, container `launchlens-db`).

**Tech Stack:** SQLAlchemy 2.0 async, GoogleVisionProvider, OpenAIVisionProvider, ClaudeProvider, StorageService, WeightManager, FHA filter, emit_event (Outbox Pattern), pytest-asyncio

---

## File Structure

```
src/launchlens/agents/
  ingestion.py     MODIFY — implement IngestionAgent (dedup, validate, state → ANALYZING)
  vision.py        MODIFY — implement VisionAgent (Tier 1 bulk + Tier 2 re-rank)
  coverage.py      MODIFY — implement CoverageAgent (required shot check)
  packaging.py     MODIFY — implement PackagingAgent (score + select hero)
  content.py       MODIFY — implement ContentAgent (Claude copy + FHA)
  brand.py         MODIFY — implement BrandAgent (template render → S3)
  learning.py      MODIFY — implement LearningAgent (weight updates from overrides)
  distribution.py  MODIFY — implement DistributionAgent (state → DELIVERED)

src/launchlens/services/
  weight_manager.py  MODIFY — implement score() replacing stub

tests/test_agents/
  __init__.py         EXISTS (from scaffold)
  conftest.py         CREATE — shared DB fixtures (listing, assets, vision_results)
  test_ingestion.py   CREATE
  test_vision.py      CREATE
  test_coverage.py    CREATE
  test_packaging.py   CREATE
  test_content.py     CREATE
  test_brand.py       CREATE
  test_learning.py    CREATE
  test_distribution.py CREATE
  test_pipeline.py    CREATE — end-to-end smoke test
```

---

## Session Injection Pattern (used by all agents)

Every agent receives a `session_factory` in its constructor. In production it defaults to `AsyncSessionLocal`. In tests we wrap the test session in a trivial async context manager so the agent sees its own "session" but actually shares the test's savepoint-rollback transaction.

```python
# Standard agent constructor pattern
from launchlens.database import AsyncSessionLocal

class SomeAgent(BaseAgent):
    agent_name = "some"

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        async with self._session_factory() as session:
            async with session.begin():
                # ... do work ...
                await emit_event(session, "some.completed", {...}, tenant_id=context.tenant_id)
        return {"status": "ok"}
```

```python
# Test session factory helper — place in tests/test_agents/conftest.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def _wrap_session(session):
    yield session

def make_session_factory(session):
    """Returns a factory that yields the given session (for testing)."""
    return lambda: _wrap_session(session)
```

---

### Task 1: IngestionAgent

**Files:**
- Modify: `src/launchlens/agents/ingestion.py`
- Create: `tests/test_agents/conftest.py`
- Create: `tests/test_agents/test_ingestion.py`

- [ ] **Step 1: Create `tests/test_agents/conftest.py`**

This establishes shared fixtures used by all agent tests.

```python
# tests/test_agents/conftest.py
import uuid
import pytest
from contextlib import asynccontextmanager
from launchlens.models.listing import Listing, ListingState
from launchlens.models.asset import Asset


@asynccontextmanager
async def _wrap_session(session):
    """Wraps an existing session to look like a session factory context manager."""
    yield session


def make_session_factory(session):
    """Returns a factory that yields the given test session."""
    return lambda: _wrap_session(session)


@pytest.fixture
async def listing(db_session):
    """A listing in UPLOADING state with one tenant."""
    tenant_id = uuid.uuid4()
    obj = Listing(
        tenant_id=tenant_id,
        address={"street": "123 Main St", "city": "Austin", "state": "TX"},
        metadata_={"beds": 3, "baths": 2, "sqft": 1800},
        state=ListingState.UPLOADING,
    )
    db_session.add(obj)
    await db_session.flush()
    return obj


@pytest.fixture
async def assets(db_session, listing):
    """Three uploaded assets for the listing."""
    items = []
    hashes = ["aaa111", "bbb222", "ccc333"]
    for i, h in enumerate(hashes):
        a = Asset(
            tenant_id=listing.tenant_id,
            listing_id=listing.id,
            file_path=f"listings/{listing.id}/photo_{i}.jpg",
            file_hash=h,
            state="uploaded",
        )
        db_session.add(a)
        items.append(a)
    await db_session.flush()
    return items
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_agents/test_ingestion.py
import pytest
from launchlens.agents.ingestion import IngestionAgent
from launchlens.agents.base import AgentContext
from launchlens.models.listing import ListingState
from launchlens.models.asset import Asset
from sqlalchemy import select
from tests.test_agents.conftest import make_session_factory


@pytest.mark.asyncio
async def test_ingestion_marks_assets_ingested(db_session, listing, assets):
    agent = IngestionAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)
    assert result["valid_count"] == 3
    assert result["duplicate_count"] == 0
    for a in assets:
        await db_session.refresh(a)
        assert a.state == "ingested"


@pytest.mark.asyncio
async def test_ingestion_deduplicates_same_hash(db_session, listing, assets):
    # Make two assets with the same hash
    assets[1].file_hash = assets[0].file_hash
    await db_session.flush()

    agent = IngestionAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)
    assert result["valid_count"] == 2
    assert result["duplicate_count"] == 1


@pytest.mark.asyncio
async def test_ingestion_transitions_listing_state(db_session, listing, assets):
    agent = IngestionAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.execute(ctx)
    await db_session.refresh(listing)
    assert listing.state == ListingState.ANALYZING
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_ingestion.py -v 2>&1 | tail -15
```
Expected: FAIL — `NotImplementedError: IngestionAgent not yet implemented`

- [ ] **Step 4: Implement IngestionAgent**

```python
# src/launchlens/agents/ingestion.py
import uuid
from sqlalchemy import select
from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.asset import Asset
from launchlens.models.listing import Listing, ListingState
from launchlens.services.events import emit_event
from .base import BaseAgent, AgentContext


class IngestionAgent(BaseAgent):
    agent_name = "ingestion"

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)
        tenant_id = context.tenant_id

        async with self._session_factory() as session:
            async with session.begin():
                # Load all uploaded assets for this listing
                result = await session.execute(
                    select(Asset).where(
                        Asset.listing_id == listing_id,
                        Asset.state == "uploaded",
                    )
                )
                assets = result.scalars().all()

                # Dedup by file_hash — keep first, mark rest as duplicate
                seen_hashes: set[str] = set()
                valid_count = 0
                duplicate_count = 0
                for asset in assets:
                    if asset.file_hash in seen_hashes:
                        asset.state = "duplicate"
                        duplicate_count += 1
                    else:
                        seen_hashes.add(asset.file_hash)
                        asset.state = "ingested"
                        valid_count += 1

                # Transition listing state
                listing = await session.get(Listing, listing_id)
                listing.state = ListingState.ANALYZING

                await emit_event(
                    session=session,
                    event_type="ingestion.completed",
                    payload={"valid_count": valid_count, "duplicate_count": duplicate_count},
                    tenant_id=tenant_id,
                    listing_id=context.listing_id,
                )

        return {"valid_count": valid_count, "duplicate_count": duplicate_count}


@activity.defn
async def ingest_photos(listing_id: str, tenant_id: str) -> dict:
    agent = IngestionAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_ingestion.py -v 2>&1 | tail -15
```
Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/agents/ingestion.py tests/test_agents/conftest.py tests/test_agents/test_ingestion.py && git commit -m "feat: implement IngestionAgent with dedup and state transition"
```

---

### Task 2: VisionAgent Tier 1 (Google Vision Bulk)

**Files:**
- Modify: `src/launchlens/agents/vision.py`
- Create: `tests/test_agents/test_vision.py`

Tier 1 runs Google Vision on every `ingested` asset. Each call returns `VisionLabel` objects which are mapped to a `VisionResult` row. A label-to-room mapping derives `room_label`. `quality_score` (0–100) is the top-label confidence × 100. `commercial_score` is the count of commercially desirable labels × 20, capped at 100. `hero_candidate = quality_score >= 70 and commercial_score >= 40`.

```python
# Mapping constants (put at module level in vision.py)
ROOM_LABEL_MAP = {
    "living room": "living_room",
    "bedroom": "bedroom",
    "kitchen": "kitchen",
    "bathroom": "bathroom",
    "dining room": "dining_room",
    "building exterior": "exterior",
    "facade": "exterior",
    "garage": "garage",
    "swimming pool": "pool",
    "backyard": "backyard",
    "office": "office",
}

COMMERCIAL_LABELS = {
    "natural light", "hardwood", "granite", "stainless steel",
    "open plan", "vaulted ceiling", "fireplace", "mountain view",
    "city view", "pool", "renovated",
}
```

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agents/test_vision.py
import uuid
import pytest
from unittest.mock import AsyncMock
from launchlens.agents.vision import VisionAgent
from launchlens.agents.base import AgentContext
from launchlens.models.vision_result import VisionResult
from launchlens.providers.base import VisionLabel
from sqlalchemy import select
from tests.test_agents.conftest import make_session_factory


def make_mock_vision_provider(labels):
    """Returns a mock VisionProvider whose analyze() always returns `labels`."""
    from unittest.mock import MagicMock
    provider = MagicMock()
    provider.analyze = AsyncMock(return_value=labels)
    return provider


@pytest.mark.asyncio
async def test_tier1_writes_vision_result_per_asset(db_session, listing, assets):
    # Set assets to ingested state
    for a in assets:
        a.state = "ingested"
    await db_session.flush()

    labels = [
        VisionLabel(name="living room", confidence=0.95, category="room"),
        VisionLabel(name="hardwood", confidence=0.88, category="feature"),
        VisionLabel(name="natural light", confidence=0.82, category="quality"),
    ]
    provider = make_mock_vision_provider(labels)
    agent = VisionAgent(
        vision_provider=provider,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.run_tier1(ctx)

    assert result == 3  # one VisionResult per asset
    rows = (await db_session.execute(select(VisionResult))).scalars().all()
    assert len(rows) == 3
    assert all(r.tier == 1 for r in rows)
    assert all(r.room_label == "living_room" for r in rows)
    assert all(r.quality_score == 95 for r in rows)  # int(0.95 * 100)


@pytest.mark.asyncio
async def test_tier1_sets_hero_candidate_on_high_quality(db_session, listing, assets):
    for a in assets:
        a.state = "ingested"
    await db_session.flush()

    # High quality + commercial labels → hero_candidate=True
    labels = [
        VisionLabel(name="building exterior", confidence=0.92, category="room"),
        VisionLabel(name="natural light", confidence=0.90, category="quality"),
        VisionLabel(name="hardwood", confidence=0.85, category="feature"),
        VisionLabel(name="stainless steel", confidence=0.80, category="feature"),
    ]
    provider = make_mock_vision_provider(labels)
    agent = VisionAgent(vision_provider=provider, session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.run_tier1(ctx)

    rows = (await db_session.execute(select(VisionResult))).scalars().all()
    assert all(r.hero_candidate is True for r in rows)


@pytest.mark.asyncio
async def test_tier1_does_not_process_non_ingested_assets(db_session, listing, assets):
    # Leave assets in "uploaded" state (not ingested)
    provider = make_mock_vision_provider([])
    agent = VisionAgent(vision_provider=provider, session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.run_tier1(ctx)
    assert result == 0
    assert provider.analyze.call_count == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_vision.py -v 2>&1 | tail -15
```
Expected: FAIL — `AttributeError: 'VisionAgent' object has no attribute 'run_tier1'`

- [ ] **Step 3: Implement VisionAgent Tier 1**

```python
# src/launchlens/agents/vision.py
import uuid
import asyncio
from sqlalchemy import select
from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.asset import Asset
from launchlens.models.vision_result import VisionResult
from launchlens.models.listing import Listing, ListingState
from launchlens.providers import get_vision_provider
from launchlens.providers.base import VisionLabel
from launchlens.services.events import emit_event
from .base import BaseAgent, AgentContext

ROOM_LABEL_MAP = {
    "living room": "living_room",
    "bedroom": "bedroom",
    "kitchen": "kitchen",
    "bathroom": "bathroom",
    "dining room": "dining_room",
    "building exterior": "exterior",
    "facade": "exterior",
    "garage": "garage",
    "swimming pool": "pool",
    "backyard": "backyard",
    "office": "office",
}

COMMERCIAL_LABELS = {
    "natural light", "hardwood", "granite", "stainless steel",
    "open plan", "vaulted ceiling", "fireplace", "mountain view",
    "city view", "pool", "renovated",
}

TIER2_CANDIDATE_LIMIT = 20


def _labels_to_vision_result(asset_id: uuid.UUID, labels: list[VisionLabel]) -> VisionResult:
    """Map VisionLabel list → VisionResult row for Tier 1."""
    top_confidence = max((l.confidence for l in labels), default=0.0)
    quality_score = int(top_confidence * 100)

    # Derive room_label from first matching label
    room_label = None
    for label in labels:
        mapped = ROOM_LABEL_MAP.get(label.name.lower())
        if mapped:
            room_label = mapped
            break

    commercial_count = sum(
        1 for l in labels if l.name.lower() in COMMERCIAL_LABELS
    )
    commercial_score = min(100, commercial_count * 20)

    is_interior = room_label not in (None, "exterior", "garage", "pool", "backyard")
    hero_candidate = quality_score >= 70 and commercial_score >= 40

    return VisionResult(
        asset_id=asset_id,
        tier=1,
        room_label=room_label,
        is_interior=is_interior,
        quality_score=quality_score,
        commercial_score=commercial_score,
        hero_candidate=hero_candidate,
        raw_labels={"labels": [{"name": l.name, "confidence": l.confidence} for l in labels]},
        model_used="google-vision-v1",
    )


class VisionAgent(BaseAgent):
    agent_name = "vision"

    def __init__(self, vision_provider=None, session_factory=None):
        self._vision_provider = vision_provider or get_vision_provider()
        self._session_factory = session_factory or AsyncSessionLocal

    async def run_tier1(self, context: AgentContext) -> int:
        """Run Google Vision on all ingested assets. Returns count of results written."""
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(Asset).where(
                        Asset.listing_id == listing_id,
                        Asset.state == "ingested",
                    )
                )
                assets = result.scalars().all()

                count = 0
                for asset in assets:
                    labels = await self._vision_provider.analyze(image_url=asset.file_path)
                    vr = _labels_to_vision_result(asset.id, labels)
                    session.add(vr)
                    count += 1

                if count > 0:
                    await emit_event(
                        session=session,
                        event_type="vision.tier1.completed",
                        payload={"asset_count": count},
                        tenant_id=context.tenant_id,
                        listing_id=context.listing_id,
                    )

        return count

    async def execute(self, context: AgentContext) -> dict:
        tier1_count = await self.run_tier1(context)
        tier2_count = await self.run_tier2(context)
        return {"tier1_count": tier1_count, "tier2_count": tier2_count}

    async def run_tier2(self, context: AgentContext) -> int:
        """GPT-4V re-ranking — implemented in Task 3."""
        return 0


@activity.defn
async def run_vision(listing_id: str, tenant_id: str) -> dict:
    agent = VisionAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_vision.py -v 2>&1 | tail -15
```
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/agents/vision.py tests/test_agents/test_vision.py && git commit -m "feat: implement VisionAgent Tier 1 (Google Vision bulk labeling)"
```

---

### Task 3: VisionAgent Tier 2 (GPT-4V Re-ranking)

**Files:**
- Modify: `src/launchlens/agents/vision.py` (implement `run_tier2`)
- Modify: `tests/test_agents/test_vision.py` (add Tier 2 tests)

Tier 2 selects the top `TIER2_CANDIDATE_LIMIT` (20) `hero_candidate=True` VisionResults from Tier 1, runs GPT-4V analysis, and creates a new `VisionResult` row at `tier=2`. The Tier 2 result may update `quality_score`, `commercial_score`, and set `hero_explanation`.

- [ ] **Step 1: Add Tier 2 tests to `tests/test_agents/test_vision.py`**

```python
# Add these tests to tests/test_agents/test_vision.py

from launchlens.models.vision_result import VisionResult as VRModel


@pytest.fixture
async def tier1_results(db_session, listing, assets):
    """Pre-populate Tier 1 VisionResults for 3 hero candidates."""
    for a in assets:
        a.state = "ingested"
        db_session.add(VRModel(
            asset_id=a.id,
            tier=1,
            room_label="living_room",
            is_interior=True,
            quality_score=85,
            commercial_score=60,
            hero_candidate=True,
            raw_labels={},
            model_used="google-vision-v1",
        ))
    await db_session.flush()


@pytest.mark.asyncio
async def test_tier2_creates_results_for_hero_candidates(db_session, listing, assets, tier1_results):
    gpt_labels = [
        VisionLabel(name="primary exterior", confidence=0.95, category="shot_type"),
        VisionLabel(name="golden hour", confidence=0.88, category="quality"),
    ]
    from unittest.mock import MagicMock
    gpt_provider = MagicMock()
    gpt_provider.analyze = AsyncMock(return_value=gpt_labels)

    agent = VisionAgent(
        vision_provider=gpt_provider,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    count = await agent.run_tier2(ctx)

    assert count == 3  # one Tier 2 result per hero candidate
    tier2_rows = (
        await db_session.execute(
            select(VRModel).where(VRModel.tier == 2)
        )
    ).scalars().all()
    assert len(tier2_rows) == 3
    assert all(r.model_used == "gpt-4o" for r in tier2_rows)


@pytest.mark.asyncio
async def test_tier2_skips_if_no_hero_candidates(db_session, listing, assets):
    """If no Tier 1 hero candidates, Tier 2 should be a no-op."""
    for a in assets:
        a.state = "ingested"
        db_session.add(VRModel(
            asset_id=a.id,
            tier=1,
            room_label="bedroom",
            is_interior=True,
            quality_score=50,  # below threshold
            commercial_score=20,
            hero_candidate=False,
            raw_labels={},
            model_used="google-vision-v1",
        ))
    await db_session.flush()

    from unittest.mock import MagicMock
    gpt_provider = MagicMock()
    gpt_provider.analyze = AsyncMock(return_value=[])
    agent = VisionAgent(vision_provider=gpt_provider, session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    count = await agent.run_tier2(ctx)

    assert count == 0
    assert gpt_provider.analyze.call_count == 0
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_vision.py::test_tier2_creates_results_for_hero_candidates tests/test_agents/test_vision.py::test_tier2_skips_if_no_hero_candidates -v 2>&1 | tail -15
```
Expected: FAIL — 1 test FAILED (`test_tier2_creates_results_for_hero_candidates`: assert 0 == 3), 1 test PASSED (`test_tier2_skips_if_no_hero_candidates` — stub already returns 0, which satisfies the no-op assertion)

- [ ] **Step 3: Implement `run_tier2` in `vision.py`**

Replace the `run_tier2` stub:

```python
async def run_tier2(self, context: AgentContext) -> int:
    """Run GPT-4V on top hero candidates from Tier 1. Returns count of Tier 2 results."""
    listing_id = uuid.UUID(context.listing_id)

    async with self._session_factory() as session:
        async with session.begin():
            # Load hero candidates from Tier 1, ordered by quality descending
            result = await session.execute(
                select(VisionResult)
                .join(Asset, VisionResult.asset_id == Asset.id)
                .where(
                    Asset.listing_id == listing_id,
                    VisionResult.tier == 1,
                    VisionResult.hero_candidate.is_(True),
                )
                .order_by(VisionResult.quality_score.desc())
                .limit(TIER2_CANDIDATE_LIMIT)
            )
            candidates = result.scalars().all()

            if not candidates:
                return 0

            count = 0
            for vr in candidates:
                asset = await session.get(Asset, vr.asset_id)
                labels = await self._vision_provider.analyze(image_url=asset.file_path)
                # Derive updated scores from GPT-4V labels
                quality_labels = [l for l in labels if l.category == "quality"]
                shot_labels = [l for l in labels if l.category == "shot_type"]

                quality_score = int(
                    (sum(l.confidence for l in quality_labels) / len(quality_labels) * 100)
                    if quality_labels else vr.quality_score
                )
                hero_explanation = quality_labels[0].name if quality_labels else None
                room_label = shot_labels[0].name if shot_labels else vr.room_label

                tier2 = VisionResult(
                    asset_id=vr.asset_id,
                    tier=2,
                    room_label=room_label,
                    is_interior=vr.is_interior,
                    quality_score=quality_score,
                    commercial_score=vr.commercial_score,
                    hero_candidate=True,
                    hero_explanation=hero_explanation,
                    raw_labels={"labels": [{"name": l.name, "confidence": l.confidence} for l in labels]},
                    model_used="gpt-4o",
                )
                session.add(tier2)
                count += 1

            if count > 0:
                await emit_event(
                    session=session,
                    event_type="vision.tier2.completed",
                    payload={"candidate_count": count},
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

    return count
```

- [ ] **Step 4: Run all vision tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_vision.py -v 2>&1 | tail -20
```
Expected: 5 tests PASS (3 Tier 1 + 2 Tier 2 — confirms no regressions to Tier 1 tests)

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/agents/vision.py tests/test_agents/test_vision.py && git commit -m "feat: implement VisionAgent Tier 2 (GPT-4V hero candidate re-ranking)"
```

---

### Task 4: CoverageAgent

**Files:**
- Modify: `src/launchlens/agents/coverage.py`
- Create: `tests/test_agents/test_coverage.py`

**Depends on:** Task 2 (VisionAgent Tier 1) — requires VisionResult rows with `tier=1` and `room_label` populated for the listing's assets.

CoverageAgent reads Tier 1 VisionResults for the listing and checks for required shot categories. For MVP, required shots are: `exterior`, `living_room`, `kitchen`, `bedroom`, `bathroom`. Missing categories are returned and emitted as a `coverage.gap` event.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agents/test_coverage.py
import pytest
import uuid
from launchlens.agents.coverage import CoverageAgent, REQUIRED_SHOTS
from launchlens.agents.base import AgentContext
from launchlens.models.vision_result import VisionResult
from sqlalchemy import select
from tests.test_agents.conftest import make_session_factory


async def _add_vision_result(db_session, asset_id, room_label):
    vr = VisionResult(
        asset_id=asset_id,
        tier=1,
        room_label=room_label,
        is_interior=room_label != "exterior",
        quality_score=80,
        commercial_score=40,
        hero_candidate=True,
        raw_labels={},
        model_used="google-vision-v1",
    )
    db_session.add(vr)
    await db_session.flush()


@pytest.mark.asyncio
async def test_coverage_returns_missing_shots(db_session, listing, assets):
    # Only add exterior and living_room — bedroom, bathroom, kitchen are missing
    await _add_vision_result(db_session, assets[0].id, "exterior")
    await _add_vision_result(db_session, assets[1].id, "living_room")
    # assets[2] has no vision result

    agent = CoverageAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert set(result["missing_shots"]) == {"kitchen", "bedroom", "bathroom"}


@pytest.mark.asyncio
async def test_coverage_returns_empty_if_all_shots_present(db_session, listing, assets):
    for asset, room in zip(assets, ["exterior", "living_room", "kitchen"]):
        await _add_vision_result(db_session, asset.id, room)
    # Add bedroom and bathroom using extra assets
    extra1 = assets[0]  # reuse — just need the asset_id concept
    await _add_vision_result(db_session, extra1.id, "bedroom")
    await _add_vision_result(db_session, extra1.id, "bathroom")

    agent = CoverageAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)
    assert result["missing_shots"] == []


@pytest.mark.asyncio
async def test_coverage_missing_shots_emitted_as_event(db_session, listing, assets):
    from launchlens.models.outbox import Outbox
    await _add_vision_result(db_session, assets[0].id, "exterior")

    agent = CoverageAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.execute(ctx)
    await db_session.flush()

    outbox_rows = (await db_session.execute(
        select(Outbox).where(Outbox.event_type == "coverage.gap")
    )).scalars().all()
    assert len(outbox_rows) == 1
    assert "missing_shots" in outbox_rows[0].payload
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_coverage.py -v 2>&1 | tail -15
```
Expected: FAIL — `NotImplementedError`

- [ ] **Step 3: Implement CoverageAgent**

```python
# src/launchlens/agents/coverage.py
import uuid
from sqlalchemy import select
from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.asset import Asset
from launchlens.models.vision_result import VisionResult
from launchlens.services.events import emit_event
from .base import BaseAgent, AgentContext

REQUIRED_SHOTS = {"exterior", "living_room", "kitchen", "bedroom", "bathroom"}


class CoverageAgent(BaseAgent):
    agent_name = "coverage"

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with session.begin():
                # Get all Tier 1 VisionResults for this listing via Asset join
                result = await session.execute(
                    select(VisionResult)
                    .join(Asset, VisionResult.asset_id == Asset.id)
                    .where(
                        Asset.listing_id == listing_id,
                        VisionResult.tier == 1,
                        VisionResult.room_label.isnot(None),
                    )
                )
                vision_results = result.scalars().all()

                present_shots = {vr.room_label for vr in vision_results}
                missing_shots = sorted(REQUIRED_SHOTS - present_shots)

                event_type = "coverage.gap" if missing_shots else "coverage.completed"
                await emit_event(
                    session=session,
                    event_type=event_type,
                    payload={"missing_shots": missing_shots, "present_shots": sorted(present_shots)},
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

        return {"missing_shots": missing_shots}


@activity.defn
async def run_coverage(listing_id: str, tenant_id: str) -> dict:
    agent = CoverageAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
```

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_coverage.py -v 2>&1 | tail -15
```
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/agents/coverage.py tests/test_agents/test_coverage.py && git commit -m "feat: implement CoverageAgent with required shot gap detection"
```

---

### Task 5: PackagingAgent + WeightManager.score()

**Files:**
- Modify: `src/launchlens/agents/packaging.py`
- Modify: `src/launchlens/services/weight_manager.py` (implement `score()`)
- Create: `tests/test_agents/test_packaging.py`

**Depends on:** Tasks 2–3 (VisionAgent) — requires VisionResult rows to exist for the listing's assets before scoring can run.

`WeightManager.score()` takes a `features` dict and returns a float 0–1. Features: `quality_score` (0–100), `commercial_score` (0–100), `room_weight` (float, from LearningWeight or 1.0 default), `hero_candidate` (bool). Formula:

```
composite = (quality_score/100 * 0.5) + (commercial_score/100 * 0.3) + (0.2 if hero_candidate else 0)
return composite * room_weight
```

PackagingAgent queries Tier 1 + Tier 2 VisionResults, scores each asset, selects the top scorer as hero and up to 24 supporting photos (MLS channel), writes `PackageSelection` rows, transitions listing to `AWAITING_REVIEW`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_agents/test_packaging.py
import pytest
import uuid
from launchlens.agents.packaging import PackagingAgent
from launchlens.agents.base import AgentContext
from launchlens.models.vision_result import VisionResult
from launchlens.models.package_selection import PackageSelection
from launchlens.models.listing import ListingState
from launchlens.services.weight_manager import WeightManager
from sqlalchemy import select
from tests.test_agents.conftest import make_session_factory


async def _add_vr(db_session, asset_id, quality=80, commercial=60, hero=True, tier=1):
    vr = VisionResult(
        asset_id=asset_id,
        tier=tier,
        room_label="living_room",
        is_interior=True,
        quality_score=quality,
        commercial_score=commercial,
        hero_candidate=hero,
        raw_labels={},
        model_used="google-vision-v1",
    )
    db_session.add(vr)
    await db_session.flush()
    return vr


def test_weight_manager_score_returns_float():
    wm = WeightManager()
    score = wm.score({"quality_score": 80, "commercial_score": 60,
                      "room_weight": 1.0, "hero_candidate": True})
    assert 0.0 <= score <= 1.0


def test_weight_manager_score_hero_scores_higher():
    wm = WeightManager()
    hero = wm.score({"quality_score": 80, "commercial_score": 60,
                     "room_weight": 1.0, "hero_candidate": True})
    non_hero = wm.score({"quality_score": 80, "commercial_score": 60,
                         "room_weight": 1.0, "hero_candidate": False})
    assert hero > non_hero


@pytest.mark.asyncio
async def test_packaging_selects_hero_asset(db_session, listing, assets):
    listing.state = ListingState.ANALYZING
    await db_session.flush()

    # asset[0] gets high scores, others get low
    await _add_vr(db_session, assets[0].id, quality=95, commercial=80, hero=True)
    await _add_vr(db_session, assets[1].id, quality=50, commercial=30, hero=False)
    await _add_vr(db_session, assets[2].id, quality=60, commercial=40, hero=False)

    agent = PackagingAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result["hero_asset_id"] == str(assets[0].id)


@pytest.mark.asyncio
async def test_packaging_writes_package_selections(db_session, listing, assets):
    listing.state = ListingState.ANALYZING
    await db_session.flush()

    for a in assets:
        await _add_vr(db_session, a.id)

    agent = PackagingAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    selections = (await db_session.execute(select(PackageSelection))).scalars().all()
    assert len(selections) == 3
    assert result["total_selected"] == 3


@pytest.mark.asyncio
async def test_packaging_transitions_listing_to_awaiting_review(db_session, listing, assets):
    listing.state = ListingState.ANALYZING
    await db_session.flush()
    for a in assets:
        await _add_vr(db_session, a.id)

    agent = PackagingAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.execute(ctx)

    await db_session.refresh(listing)
    assert listing.state == ListingState.AWAITING_REVIEW
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_packaging.py -v 2>&1 | tail -15
```
Expected: FAIL — WeightManager score tests may pass partially; PackagingAgent will raise `NotImplementedError`.

- [ ] **Step 3: Implement `WeightManager.score()`**

Replace the stub in `src/launchlens/services/weight_manager.py`:

```python
def score(self, features: dict) -> float:
    """
    Composite scoring for photo selection.
    Formula: (quality*0.5 + commercial*0.3 + hero_bonus*0.2) * room_weight
    Clamped to [0.0, 1.0].
    """
    quality = features.get("quality_score", 50) / 100.0
    commercial = features.get("commercial_score", 50) / 100.0
    hero_bonus = 1.0 if features.get("hero_candidate", False) else 0.0
    room_weight = features.get("room_weight", 1.0)

    composite = (quality * 0.5) + (commercial * 0.3) + (hero_bonus * 0.2)
    return min(1.0, max(0.0, composite * room_weight))
```

- [ ] **Step 4: Implement PackagingAgent**

```python
# src/launchlens/agents/packaging.py
import uuid
from sqlalchemy import select
from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.asset import Asset
from launchlens.models.vision_result import VisionResult
from launchlens.models.listing import Listing, ListingState
from launchlens.models.package_selection import PackageSelection
from launchlens.services.events import emit_event
from launchlens.services.weight_manager import WeightManager
from .base import BaseAgent, AgentContext

MLS_MAX_PHOTOS = 25  # 1 hero + 24 supporting


class PackagingAgent(BaseAgent):
    agent_name = "packaging"

    def __init__(self, session_factory=None, weight_manager=None):
        self._session_factory = session_factory or AsyncSessionLocal
        self._wm = weight_manager or WeightManager()

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with session.begin():
                # Load best VisionResult per asset (prefer Tier 2 over Tier 1)
                result = await session.execute(
                    select(VisionResult)
                    .join(Asset, VisionResult.asset_id == Asset.id)
                    .where(Asset.listing_id == listing_id)
                    .order_by(VisionResult.tier.desc(), VisionResult.quality_score.desc())
                )
                all_vrs = result.scalars().all()

                # Deduplicate: keep best tier result per asset
                seen: dict[uuid.UUID, VisionResult] = {}
                for vr in all_vrs:
                    if vr.asset_id not in seen:
                        seen[vr.asset_id] = vr

                # Score each asset
                scored = []
                for asset_id, vr in seen.items():
                    features = {
                        "quality_score": vr.quality_score or 50,
                        "commercial_score": vr.commercial_score or 50,
                        "hero_candidate": vr.hero_candidate or False,
                        "room_weight": 1.0,  # TODO: load from LearningWeight
                    }
                    score = self._wm.score(features)
                    scored.append((score, asset_id, vr))

                scored.sort(key=lambda x: x[0], reverse=True)
                top = scored[:MLS_MAX_PHOTOS]

                hero_asset_id = str(top[0][1]) if top else None

                # Write PackageSelection rows
                for position, (score, asset_id, vr) in enumerate(top):
                    channel = "mls"
                    ps = PackageSelection(
                        tenant_id=uuid.UUID(context.tenant_id),
                        listing_id=listing_id,
                        asset_id=asset_id,
                        channel=channel,
                        position=position,
                        selected_by="ai",
                        composite_score=score,
                    )
                    session.add(ps)

                # Transition listing state
                listing = await session.get(Listing, listing_id)
                listing.state = ListingState.AWAITING_REVIEW

                await emit_event(
                    session=session,
                    event_type="packaging.completed",
                    payload={"hero_asset_id": hero_asset_id, "total_selected": len(top)},
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

        return {"hero_asset_id": hero_asset_id, "total_selected": len(top)}


@activity.defn
async def run_packaging(listing_id: str, tenant_id: str) -> dict:
    agent = PackagingAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
```

- [ ] **Step 5: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_packaging.py -v 2>&1 | tail -15
```
Expected: 5 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/agents/packaging.py src/launchlens/services/weight_manager.py tests/test_agents/test_packaging.py && git commit -m "feat: implement PackagingAgent and WeightManager.score()"
```

---

### Task 6: ContentAgent

**Files:**
- Modify: `src/launchlens/agents/content.py`
- Create: `tests/test_agents/test_content.py`

ContentAgent reads listing metadata + top VisionResult labels, builds a prompt, calls `ClaudeProvider.complete()`, then runs `fha_check()`. If FHA fails, it retries once with an explicit constraint appended to the prompt. Returns the copy as a dict.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agents/test_content.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from launchlens.agents.content import ContentAgent
from launchlens.agents.base import AgentContext
from launchlens.models.vision_result import VisionResult
from tests.test_agents.conftest import make_session_factory


async def _add_vr(db_session, asset_id, room_label="living_room", quality=80):
    vr = VisionResult(
        asset_id=asset_id, tier=1, room_label=room_label,
        is_interior=True, quality_score=quality, commercial_score=60,
        hero_candidate=True, raw_labels={"labels": [{"name": "hardwood", "confidence": 0.9}]},
        model_used="google-vision-v1",
    )
    db_session.add(vr)
    await db_session.flush()


def make_llm_provider(response="Beautiful 3-bedroom home with modern finishes."):
    provider = MagicMock()
    provider.complete = AsyncMock(return_value=response)
    return provider


@pytest.mark.asyncio
async def test_content_returns_copy(db_session, listing, assets):
    for a in assets:
        await _add_vr(db_session, a.id)

    provider = make_llm_provider()
    agent = ContentAgent(llm_provider=provider, session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert "copy" in result
    assert len(result["copy"]) > 0
    assert result["fha_passed"] is True


@pytest.mark.asyncio
async def test_content_retries_on_fha_violation(db_session, listing, assets):
    for a in assets:
        await _add_vr(db_session, a.id)

    # First call returns FHA violation, second returns clean copy
    provider = MagicMock()
    provider.complete = AsyncMock(side_effect=[
        "Perfect for families looking for a safe neighborhood.",
        "Stunning home with modern kitchen and open floor plan.",
    ])
    agent = ContentAgent(llm_provider=provider, session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert provider.complete.call_count == 2
    assert result["fha_passed"] is True
    assert "family" not in result["copy"].lower()


@pytest.mark.asyncio
async def test_content_emits_event(db_session, listing, assets):
    from launchlens.models.outbox import Outbox
    from sqlalchemy import select

    for a in assets:
        await _add_vr(db_session, a.id)

    provider = make_llm_provider()
    agent = ContentAgent(llm_provider=provider, session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.execute(ctx)
    await db_session.flush()

    rows = (await db_session.execute(
        select(Outbox).where(Outbox.event_type == "content.completed")
    )).scalars().all()
    assert len(rows) == 1
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_content.py -v 2>&1 | tail -15
```
Expected: FAIL — `NotImplementedError`

- [ ] **Step 3: Implement ContentAgent**

```python
# src/launchlens/agents/content.py
import uuid
from sqlalchemy import select
from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.asset import Asset
from launchlens.models.listing import Listing
from launchlens.models.vision_result import VisionResult
from launchlens.providers import get_llm_provider
from launchlens.services.events import emit_event
from launchlens.services.fha_filter import fha_check
from .base import BaseAgent, AgentContext

_PROMPT_TEMPLATE = """\
Write a compelling real estate listing description for the following property.
Be specific and factual. Do not use Fair Housing Act prohibited language.

Property details:
{metadata}

Key features identified from photos:
{photo_features}

Write a 2-3 sentence description."""

_FHA_RETRY_SUFFIX = (
    "\n\nIMPORTANT: The previous attempt contained language that may violate the Fair Housing Act. "
    "Rewrite without referencing families, schools, neighborhood safety, or religion."
)


class ContentAgent(BaseAgent):
    agent_name = "content"

    def __init__(self, llm_provider=None, session_factory=None):
        self._llm_provider = llm_provider or get_llm_provider()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with session.begin():
                listing = await session.get(Listing, listing_id)

                # Gather top vision labels for the prompt
                result = await session.execute(
                    select(VisionResult)
                    .join(Asset, VisionResult.asset_id == Asset.id)
                    .where(
                        Asset.listing_id == listing_id,
                        VisionResult.tier == 1,
                    )
                    .order_by(VisionResult.quality_score.desc())
                    .limit(5)
                )
                vrs = result.scalars().all()
                features_text = ", ".join(
                    f"{vr.room_label} (q={vr.quality_score})" for vr in vrs if vr.room_label
                )

                prompt = _PROMPT_TEMPLATE.format(
                    metadata=str(listing.metadata_),
                    photo_features=features_text or "modern interior",
                )

                # Generate copy, retry once on FHA violation
                copy = await self._llm_provider.complete(
                    prompt=prompt, context=listing.metadata_
                )
                fha_result = fha_check({"copy": copy})

                if not fha_result.passed:
                    copy = await self._llm_provider.complete(
                        prompt=prompt + _FHA_RETRY_SUFFIX, context=listing.metadata_
                    )
                    fha_result = fha_check({"copy": copy})

                await emit_event(
                    session=session,
                    event_type="content.completed",
                    payload={"fha_passed": fha_result.passed, "copy_length": len(copy)},
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

        return {"copy": copy, "fha_passed": fha_result.passed}


@activity.defn
async def run_content(listing_id: str, tenant_id: str) -> dict:
    agent = ContentAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
```

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_content.py -v 2>&1 | tail -15
```
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/agents/content.py tests/test_agents/test_content.py && git commit -m "feat: implement ContentAgent with Claude copy generation and FHA retry"
```

---

### Task 7: BrandAgent

**Files:**
- Modify: `src/launchlens/agents/brand.py`
- Create: `tests/test_agents/test_brand.py`

BrandAgent reads the hero `PackageSelection` for the listing, calls `TemplateProvider.render()` to produce a PDF/PNG flyer, uploads to S3, and emits `brand.completed`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agents/test_brand.py
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from launchlens.agents.brand import BrandAgent
from launchlens.agents.base import AgentContext
from launchlens.models.package_selection import PackageSelection
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
async def test_brand_renders_and_uploads_flyer(db_session, listing, assets, hero_selection):
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
async def test_brand_emits_event(db_session, listing, assets, hero_selection):
    from launchlens.models.outbox import Outbox
    from sqlalchemy import select

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
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_brand.py -v 2>&1 | tail -15
```
Expected: FAIL — `NotImplementedError`

- [ ] **Step 3: Implement BrandAgent**

```python
# src/launchlens/agents/brand.py
import uuid
from sqlalchemy import select
from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.listing import Listing
from launchlens.models.package_selection import PackageSelection
from launchlens.providers import get_template_provider
from launchlens.services.events import emit_event
from launchlens.services.storage import StorageService
from .base import BaseAgent, AgentContext


class BrandAgent(BaseAgent):
    agent_name = "brand"

    def __init__(self, template_provider=None, storage_service=None, session_factory=None):
        self._template_provider = template_provider or get_template_provider()
        self._storage = storage_service or StorageService()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with session.begin():
                listing = await session.get(Listing, listing_id)

                # Find hero photo (position=0)
                result = await session.execute(
                    select(PackageSelection).where(
                        PackageSelection.listing_id == listing_id,
                        PackageSelection.position == 0,
                    )
                )
                hero = result.scalar_one_or_none()
                hero_asset_id = str(hero.asset_id) if hero else None

                # Render flyer
                flyer_bytes = await self._template_provider.render(
                    template_id="flyer-standard",
                    data={
                        "listing_id": str(listing_id),
                        "address": listing.address,
                        "metadata": listing.metadata_,
                        "hero_asset_id": hero_asset_id,
                    },
                )

                # Upload to S3
                s3_key = f"listings/{listing_id}/flyer.pdf"
                self._storage.upload(key=s3_key, data=flyer_bytes, content_type="application/pdf")

                await emit_event(
                    session=session,
                    event_type="brand.completed",
                    payload={"flyer_s3_key": s3_key},
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

        return {"flyer_s3_key": s3_key}


@activity.defn
async def run_brand(listing_id: str, tenant_id: str) -> dict:
    agent = BrandAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
```

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_brand.py -v 2>&1 | tail -15
```
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/agents/brand.py tests/test_agents/test_brand.py && git commit -m "feat: implement BrandAgent with template render and S3 upload"
```

---

### Task 8: LearningAgent

**Files:**
- Modify: `src/launchlens/agents/learning.py`
- Create: `tests/test_agents/test_learning.py`

LearningAgent is triggered after a human reviewer approves or overrides the AI package. It reads `Event` rows with event_type `package.override.*` for the listing, calls `WeightManager.apply_update()`, and upserts `LearningWeight` rows. It also increments `labeled_listing_count`.

Override event types → WeightManager actions:
- `package.override.approved` → `"approval"`
- `package.override.rejected` → `"rejection"`
- `package.override.swap_to` → `"swap_to"`
- `package.override.swap_from` → `"swap_from"`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agents/test_learning.py
import pytest
import uuid
from launchlens.agents.learning import LearningAgent
from launchlens.agents.base import AgentContext
from launchlens.models.event import Event
from launchlens.models.learning_weight import LearningWeight
from sqlalchemy import select
from datetime import datetime, timezone
from tests.test_agents.conftest import make_session_factory


async def _add_override_event(db_session, listing, event_type, room_label="living_room"):
    ev = Event(
        event_type=event_type,
        payload={"room_label": room_label},
        tenant_id=listing.tenant_id,
        listing_id=listing.id,
        occurred_at=datetime.now(timezone.utc),
    )
    db_session.add(ev)
    await db_session.flush()


@pytest.mark.asyncio
async def test_learning_creates_weight_on_first_approval(db_session, listing, assets):
    await _add_override_event(db_session, listing, "package.override.approved", "living_room")

    agent = LearningAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result["weights_updated"] == 1
    weights = (await db_session.execute(select(LearningWeight))).scalars().all()
    assert len(weights) == 1
    assert weights[0].room_label == "living_room"
    # approval should increase weight above 1.0 baseline
    assert weights[0].weight > 1.0


@pytest.mark.asyncio
async def test_learning_upserts_existing_weight(db_session, listing, assets):
    # Pre-create a weight row
    existing = LearningWeight(
        tenant_id=listing.tenant_id,
        room_label="kitchen",
        weight=1.1,
        labeled_listing_count=5,
    )
    db_session.add(existing)
    await db_session.flush()

    await _add_override_event(db_session, listing, "package.override.rejected", "kitchen")

    agent = LearningAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.execute(ctx)

    await db_session.refresh(existing)
    # rejection should decrease weight
    assert existing.weight < 1.1


@pytest.mark.asyncio
async def test_learning_increments_labeled_listing_count(db_session, listing, assets):
    await _add_override_event(db_session, listing, "package.override.approved", "bedroom")

    agent = LearningAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.execute(ctx)

    weights = (await db_session.execute(select(LearningWeight))).scalars().all()
    assert weights[0].labeled_listing_count == 1
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_learning.py -v 2>&1 | tail -15
```
Expected: FAIL — `NotImplementedError`

- [ ] **Step 3: Implement LearningAgent**

```python
# src/launchlens/agents/learning.py
import uuid
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.event import Event
from launchlens.models.learning_weight import LearningWeight
from launchlens.services.events import emit_event
from launchlens.services.weight_manager import WeightManager
from .base import BaseAgent, AgentContext

OVERRIDE_ACTION_MAP = {
    "package.override.approved": "approval",
    "package.override.rejected": "rejection",
    "package.override.swap_to": "swap_to",
    "package.override.swap_from": "swap_from",
}


class LearningAgent(BaseAgent):
    agent_name = "learning"

    def __init__(self, session_factory=None, weight_manager=None):
        self._session_factory = session_factory or AsyncSessionLocal
        self._wm = weight_manager or WeightManager()

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)
        tenant_id = uuid.UUID(context.tenant_id)

        async with self._session_factory() as session:
            async with session.begin():
                # Load override events for this listing
                result = await session.execute(
                    select(Event).where(
                        Event.listing_id == listing_id,
                        Event.event_type.in_(list(OVERRIDE_ACTION_MAP.keys())),
                    )
                )
                events = result.scalars().all()

                weights_updated = 0
                for event in events:
                    room_label = event.payload.get("room_label")
                    if not room_label:
                        continue

                    action = OVERRIDE_ACTION_MAP[event.event_type]

                    # Load or default current weight
                    existing = (await session.execute(
                        select(LearningWeight).where(
                            LearningWeight.tenant_id == tenant_id,
                            LearningWeight.room_label == room_label,
                        )
                    )).scalar_one_or_none()

                    current_weight = existing.weight if existing else 1.0
                    new_weight = self._wm.apply_update(current_weight, action)

                    if existing:
                        existing.weight = new_weight
                        existing.labeled_listing_count += 1
                    else:
                        session.add(LearningWeight(
                            tenant_id=tenant_id,
                            room_label=room_label,
                            weight=new_weight,
                            labeled_listing_count=1,
                        ))

                    weights_updated += 1

                if weights_updated > 0:
                    await emit_event(
                        session=session,
                        event_type="learning.completed",
                        payload={"weights_updated": weights_updated},
                        tenant_id=context.tenant_id,
                        listing_id=context.listing_id,
                    )

        return {"weights_updated": weights_updated}


@activity.defn
async def run_learning(listing_id: str, tenant_id: str) -> dict:
    agent = LearningAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
```

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_learning.py -v 2>&1 | tail -15
```
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/agents/learning.py tests/test_agents/test_learning.py && git commit -m "feat: implement LearningAgent with weight upsert from override events"
```

---

### Task 9: DistributionAgent

**Files:**
- Modify: `src/launchlens/agents/distribution.py`
- Create: `tests/test_agents/test_distribution.py`

DistributionAgent is the final step. It transitions `Listing.state` from `APPROVED` → `DELIVERED` and emits `pipeline.completed`. The `DELIVERING` intermediate state is intentionally skipped for MVP (no async MLS submission yet — distribution is synchronous state change only). The `DELIVERING` state will be used in a future plan when MLS API submission is added.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agents/test_distribution.py
import pytest
from launchlens.agents.distribution import DistributionAgent
from launchlens.agents.base import AgentContext
from launchlens.models.listing import ListingState
from launchlens.models.outbox import Outbox
from sqlalchemy import select
from tests.test_agents.conftest import make_session_factory


@pytest.mark.asyncio
async def test_distribution_transitions_to_delivered(db_session, listing, assets):
    listing.state = ListingState.APPROVED
    await db_session.flush()

    agent = DistributionAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    await db_session.refresh(listing)
    assert listing.state == ListingState.DELIVERED
    assert result["status"] == "delivered"


@pytest.mark.asyncio
async def test_distribution_emits_pipeline_completed(db_session, listing, assets):
    listing.state = ListingState.APPROVED
    await db_session.flush()

    agent = DistributionAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.execute(ctx)
    await db_session.flush()

    rows = (await db_session.execute(
        select(Outbox).where(Outbox.event_type == "pipeline.completed")
    )).scalars().all()
    assert len(rows) == 1
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_distribution.py -v 2>&1 | tail -15
```
Expected: FAIL — `NotImplementedError`

- [ ] **Step 3: Implement DistributionAgent**

```python
# src/launchlens/agents/distribution.py
import uuid
from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.listing import Listing, ListingState
from launchlens.services.events import emit_event
from .base import BaseAgent, AgentContext


class DistributionAgent(BaseAgent):
    agent_name = "distribution"

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with session.begin():
                listing = await session.get(Listing, listing_id)
                listing.state = ListingState.DELIVERED

                await emit_event(
                    session=session,
                    event_type="pipeline.completed",
                    payload={"listing_id": context.listing_id},
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

        return {"status": "delivered"}


@activity.defn
async def run_distribution(listing_id: str, tenant_id: str) -> dict:
    agent = DistributionAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
```

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_distribution.py -v 2>&1 | tail -15
```
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/agents/distribution.py tests/test_agents/test_distribution.py && git commit -m "feat: implement DistributionAgent with DELIVERED state transition"
```

---

### Task 10: End-to-End Pipeline Smoke Test + Tag

**Files:**
- Create: `tests/test_agents/test_pipeline.py`

Run all agents in sequence against the real test DB with mock providers. Verifies the full state machine progression: UPLOADING → ANALYZING → AWAITING_REVIEW → APPROVED → DELIVERED.

- [ ] **Step 1: Write the end-to-end test**

```python
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

    # Mock providers
    def make_vision_labels(room_label):
        return [
            VisionLabel(name=room_label.replace("_", " "), confidence=0.95, category="room"),
            VisionLabel(name="natural light", confidence=0.88, category="quality"),
            VisionLabel(name="hardwood", confidence=0.82, category="feature"),
        ]

    # Each asset gets labels matching its shot type
    call_count = [0]
    async def mock_analyze(image_url):
        idx = call_count[0] % len(shot_hashes)
        call_count[0] += 1
        return make_vision_labels(shot_hashes[idx][1])

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
    assert r["valid_count"] == 5
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
```

- [ ] **Step 2: Run the smoke test**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_agents/test_pipeline.py -v 2>&1 | tail -25
```
Expected: 1 test PASS

- [ ] **Step 3: Run full test suite**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest --tb=short -q 2>&1 | tail -15
```
Expected: All agent tests pass. Note total count.

- [ ] **Step 4: Commit and tag**

```bash
cd /c/Users/Jeff/launchlens && git add tests/test_agents/test_pipeline.py && git commit -m "feat: add end-to-end pipeline smoke test" && git tag v0.3.0-agent-pipeline && echo "Tagged v0.3.0-agent-pipeline"
```

---

## NOT in scope

- Temporal workflow wiring (ListingPipeline.run() calling all activities in sequence) — needs Temporal server running; covered in API Endpoints plan
- LearningAgent loading actual `LearningWeight` rows into PackagingAgent scoring — PackagingAgent uses `room_weight=1.0` hardcoded; weight lookup is a TODO
- BrandAgent Canva integration — MockTemplateProvider used; Canva is a deferred TODO
- Near-duplicate detection via image embeddings — dedup is hash-only for MVP
- Streaming response from content generation — ClaudeProvider returns full string
- DistributionAgent MLS API submission — currently only transitions state

## What already exists

- All 8 agent stub files in `src/launchlens/agents/` — this plan replaces `NotImplementedError` bodies
- `WeightManager` with `blend()` and `apply_update()` fully implemented — only `score()` is stubbed
- `VisionResult`, `Asset`, `Listing`, `PackageSelection`, `LearningWeight`, `Event`, `Outbox` models all in place
- `emit_event()`, `StorageService`, `fha_check()`, provider factory all ready from Core Services plan
- `db_session` fixture in `tests/conftest.py` for test DB access
