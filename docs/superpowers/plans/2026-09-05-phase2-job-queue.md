# Phase 2: Postgres Job Queue Replaces Temporal — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the listing pipeline from a `pipeline_jobs` table and an in-process worker loop, so Temporal (and Temporal Cloud) can be deleted and every stuck-state bug becomes a visible `failed` job.

**Architecture:** One table holds one row per (listing, step). A declarative step list (`pipeline/definition.py`) replaces the 300-line workflow; a runner (`pipeline/runner.py`) claims runnable jobs with `SELECT ... FOR UPDATE SKIP LOCKED`, runs the existing agents unchanged as step callables (`pipeline/steps.py`), and enqueues nothing new because all rows are inserted up front and simply become runnable as their prerequisites finish. The human review gate is a `waiting` row that the approve endpoint marks `done`. The worker loop runs as an asyncio task inside the API process (Render free tier has no workers) and can also run standalone.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async + asyncpg, Alembic, pytest + pytest-asyncio (real Postgres on localhost:5433), existing agents under `src/listingjet/agents/`.

**Spec:** `docs/superpowers/specs/2026-09-05-free-tier-rework-design.md` (section "Phase 2: job queue replaces Temporal").

## Global Constraints

- Branch `feat/job-queue` (created off `fix/security-week1`, PR #306, because it depends on Phase 1). Never push to `main`; open a PR at the end and do not merge. If #306 has merged by then, rebase onto `main` first.
- Every Bash call passes an explicit `timeout`. Full pytest ≈ 380 s: use `timeout: 600000`.
- Tooling on this machine: `.venv/Scripts/python.exe -m pytest <paths> -q --tb=short -p no:cacheprovider` from the repo root; `.venv/Scripts/ruff.exe check src tests alembic`; `.venv/Scripts/alembic.exe <cmd>`. Postgres dev DB on localhost:5432 (migrated to 052) and test DB on localhost:5433 are already running; `.env` exists. No Docker.
- Alembic head is `052_tenant_indexes`. The new migration is `053_pipeline_jobs` with `down_revision = "052_tenant_indexes"`.
- Agents are NOT rewritten in this phase (that is Phases 4–6). Step names in this phase match the current agents: `ingestion, vision_tier1, property_verification, vision_tier2, coverage, virtual_staging, floorplan, dollhouse_render, packaging, photo_compliance, video, await_review, content, brand, social_content, chapters, social_cuts, mls_export, distribution, microsite, learning, social_event, health_score, performance_intelligence`.
- Job status values are exactly: `queued`, `waiting`, `running`, `done`, `failed`, `skipped`, `cancelled`.
- Commit messages end with:
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01FN81v1ehP7Snv3UsWaRf9D
  ```

## Findings that shape this plan

- `src/listingjet/activities/social_event.py:19` imports `get_async_session` from `listingjet.database`, which does not exist. The step has failed on every run (tolerated by the workflow). Task 3 fixes it with `AsyncSessionLocal`.
- `DemoCleanupWorkflow` calls `cleanup_expired_demos(session)` without `storage`, so R2/S3 objects are never deleted. Task 7 passes `get_storage()`.
- `listings_media.py:158` and `admin_listings.py:151` start the pipeline without `billing_model`/`enabled_addons`, so credit-billing gating never applied on those paths. Task 8 loads tenant + addons the same way `listings_draft.py:185-200` does (copy that helper).
- Frontend `PipelineStep.status` already accepts `"failed"`; the new status endpoint adds an `error` field and keeps the existing shape.
- Nothing in `tests/` calls `/pipeline-status`; Task 8 adds coverage.

## File structure

| File | Responsibility |
|---|---|
| `src/listingjet/models/pipeline_job.py` | `PipelineJob` ORM model + `JobStatus` enum |
| `alembic/versions/053_pipeline_jobs.py` | table + indexes |
| `src/listingjet/pipeline/__init__.py` | package marker, re-exports `PIPELINE`, `enqueue_pipeline`, `complete_review` |
| `src/listingjet/pipeline/definition.py` | `Step` dataclass, `PIPELINE` list, `validate_pipeline()` |
| `src/listingjet/pipeline/steps.py` | `StepContext`, one async callable per step wrapping an agent (replaces `activities/pipeline.py` + `activities/social_event.py`) |
| `src/listingjet/pipeline/runner.py` | enqueue, claim, run, failure/retry, review gate, retry/cancel helpers, stale reclaim, `worker_loop`, periodic tasks |
| `src/listingjet/pipeline/worker.py` | standalone entry (`python -m listingjet.pipeline.worker`) with heartbeat file |
| `src/listingjet/api/listings_workflow.py` | approve/retry/cancel/pipeline-status call the runner helpers |
| `tests/test_pipeline/` | definition, steps, runner, worker tests (replaces `tests/test_workflows/`) |
| `scripts/seed_sample_listing.py` | creates tenant + user + listing + 12 generated photos for a local run |

---

### Task 1: `PipelineJob` model and migration 053

**Files:**
- Create: `src/listingjet/models/pipeline_job.py`
- Modify: `src/listingjet/models/__init__.py` (add export)
- Create: `alembic/versions/053_pipeline_jobs.py`
- Test: `tests/test_models/test_pipeline_job.py`

**Interfaces:**
- Produces: `PipelineJob` with columns `id, tenant_id, listing_id, step, status, attempts, max_attempts, run_after, locked_by, locked_at, payload, result, error, started_at, finished_at, created_at, updated_at`; `JobStatus` str enum with the seven values from Global Constraints; unique constraint `(listing_id, step)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models/test_pipeline_job.py
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from listingjet.models.pipeline_job import JobStatus, PipelineJob


def test_job_status_values():
    assert {s.value for s in JobStatus} == {
        "queued", "waiting", "running", "done", "failed", "skipped", "cancelled",
    }


@pytest.mark.asyncio
async def test_pipeline_job_defaults_and_unique_step(db_session):
    listing_id, tenant_id = uuid.uuid4(), uuid.uuid4()
    job = PipelineJob(tenant_id=tenant_id, listing_id=listing_id, step="ingestion")
    db_session.add(job)
    await db_session.flush()

    row = (await db_session.execute(select(PipelineJob).where(PipelineJob.id == job.id))).scalar_one()
    assert row.status == JobStatus.QUEUED
    assert row.attempts == 0
    assert row.max_attempts == 3
    assert row.run_after is not None
    assert row.payload == {}
    assert row.result is None
    assert row.locked_by is None

    db_session.add(PipelineJob(tenant_id=tenant_id, listing_id=listing_id, step="ingestion"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()
```

Check how `db_session` is defined in `tests/conftest.py` (it creates tables with `Base.metadata.create_all` on the 5433 DB); the model must be imported by `listingjet.models` so `create_all` sees it.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_models/test_pipeline_job.py -q -p no:cacheprovider` (timeout 120000)
Expected: FAIL with `ModuleNotFoundError: listingjet.models.pipeline_job`.

- [ ] **Step 3: Implement the model**

```python
# src/listingjet/models/pipeline_job.py
"""One row per (listing, pipeline step). The worker loop claims rows with
SELECT ... FOR UPDATE SKIP LOCKED; see listingjet.pipeline.runner."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from listingjet.database import Base


class JobStatus(str, enum.Enum):
    QUEUED = "queued"       # runnable once prerequisites are satisfied
    WAITING = "waiting"     # human gate; completed by an API call, never by the worker
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"     # gated off (add-on / billing) — counts as satisfied
    CANCELLED = "cancelled" # listing failed or was cancelled before this ran


class PipelineJob(Base):
    __tablename__ = "pipeline_jobs"
    __table_args__ = (UniqueConstraint("listing_id", "step", name="uq_pipeline_jobs_listing_step"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    step: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, name="pipeline_job_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=JobStatus.QUEUED, index=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

Add to `src/listingjet/models/__init__.py`:

```python
from .pipeline_job import PipelineJob                          # noqa
```

- [ ] **Step 4: Write the migration**

```python
# alembic/versions/053_pipeline_jobs.py
"""pipeline_jobs table (replaces Temporal)

Revision ID: 053_pipeline_jobs
Revises: 052_tenant_indexes
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "053_pipeline_jobs"
down_revision = "052_tenant_indexes"
branch_labels = None
depends_on = None

_STATUS = ("queued", "waiting", "running", "done", "failed", "skipped", "cancelled")


def upgrade() -> None:
    status_enum = postgresql.ENUM(*_STATUS, name="pipeline_job_status", create_type=False)
    status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "pipeline_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step", sa.String(64), nullable=False),
        sa.Column("status", status_enum, nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("run_after", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("locked_by", sa.String(128), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("listing_id", "step", name="uq_pipeline_jobs_listing_step"),
    )
    op.create_index("ix_pipeline_jobs_tenant_id", "pipeline_jobs", ["tenant_id"])
    op.create_index("ix_pipeline_jobs_listing_id", "pipeline_jobs", ["listing_id"])
    op.create_index("ix_pipeline_jobs_status", "pipeline_jobs", ["status"])
    # The worker's claim query: queued rows ordered by run_after.
    op.create_index("ix_pipeline_jobs_claim", "pipeline_jobs", ["status", "run_after"])


def downgrade() -> None:
    op.drop_index("ix_pipeline_jobs_claim", table_name="pipeline_jobs")
    op.drop_index("ix_pipeline_jobs_status", table_name="pipeline_jobs")
    op.drop_index("ix_pipeline_jobs_listing_id", table_name="pipeline_jobs")
    op.drop_index("ix_pipeline_jobs_tenant_id", table_name="pipeline_jobs")
    op.drop_table("pipeline_jobs")
    postgresql.ENUM(name="pipeline_job_status").drop(op.get_bind(), checkfirst=True)
```

Look at `alembic/versions/024_*.py` (which added the `CANCELLED` listing state) for how this repo has handled Postgres enums before, and match its style if it differs.

- [ ] **Step 5: Run tests and the migration**

Run: `.venv/Scripts/python.exe -m pytest tests/test_models/test_pipeline_job.py -q -p no:cacheprovider` (timeout 120000). Expected: PASS.
Run: `.venv/Scripts/alembic.exe heads` → exactly `053_pipeline_jobs (head)`.
Run: `.venv/Scripts/alembic.exe upgrade head && .venv/Scripts/alembic.exe downgrade -1 && .venv/Scripts/alembic.exe upgrade head` (timeout 120000) against the dev DB. Expected: no errors. (Alembic is configured to read `DATABASE_URL_SYNC` from `.env`.)
Run: `.venv/Scripts/ruff.exe check src tests alembic`.

- [ ] **Step 6: Commit**

```bash
git add src/listingjet/models/pipeline_job.py src/listingjet/models/__init__.py alembic/versions/053_pipeline_jobs.py tests/test_models/test_pipeline_job.py
git commit -m "feat(pipeline): PipelineJob model and migration 053"
```

---

### Task 2: Pipeline definition

**Files:**
- Create: `src/listingjet/pipeline/__init__.py` (empty for now; Task 4 fills it)
- Create: `src/listingjet/pipeline/definition.py`
- Test: `tests/test_pipeline/__init__.py` (empty), `tests/test_pipeline/test_definition.py`

**Interfaces:**
- Produces:
  ```python
  @dataclass(frozen=True)
  class Step:
      name: str
      requires: tuple[str, ...] = ()
      timeout_s: int = 600
      max_attempts: int = 3
      optional: bool = False        # failure does not fail the listing
      gate: str | None = None       # "addon:<slug>" | "video" | "review"
  PIPELINE: list[Step]
  STEP_INDEX: dict[str, Step]
  def validate_pipeline(steps: list[Step]) -> None   # raises ValueError
  def topological_order(steps: list[Step]) -> list[str]
  ```
  Gates mean: `addon:<slug>` → skipped unless slug in enabled addons; `video` → skipped when `billing_model == "credit"` and `"ai_video_tour"` not in addons (the current workflow rule); `review` → the human gate row, inserted as `waiting`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pipeline/test_definition.py
import pytest

from listingjet.pipeline.definition import PIPELINE, STEP_INDEX, Step, topological_order, validate_pipeline


def test_pipeline_is_valid_and_has_expected_steps():
    validate_pipeline(PIPELINE)
    names = [s.name for s in PIPELINE]
    assert names[0] == "ingestion"
    assert "await_review" in names and "distribution" in names
    assert len(names) == len(set(names))
    assert STEP_INDEX["await_review"].gate == "review"
    assert STEP_INDEX["video"].gate == "video"
    assert STEP_INDEX["virtual_staging"].gate == "addon:virtual_staging"


def test_required_steps_are_not_optional():
    for name in ("ingestion", "vision_tier1", "vision_tier2", "coverage", "floorplan",
                 "packaging", "content", "mls_export", "distribution"):
        assert STEP_INDEX[name].optional is False, name


def test_post_approval_steps_depend_on_review_gate():
    order = topological_order(PIPELINE)
    assert order.index("await_review") < order.index("content")
    assert order.index("content") < order.index("mls_export")
    assert order.index("mls_export") < order.index("distribution")


def test_validate_rejects_unknown_dependency():
    bad = [Step("a"), Step("b", requires=("zzz",))]
    with pytest.raises(ValueError, match="zzz"):
        validate_pipeline(bad)


def test_validate_rejects_cycle():
    bad = [Step("a", requires=("b",)), Step("b", requires=("a",))]
    with pytest.raises(ValueError, match="cycle"):
        validate_pipeline(bad)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_pipeline -q -p no:cacheprovider` (timeout 60000)
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Implement**

```python
# src/listingjet/pipeline/definition.py
"""Declarative listing pipeline. Replaces workflows/listing_pipeline.py.

Each Step becomes one pipeline_jobs row when a listing is enqueued. A row is
runnable when every `requires` row is satisfied: done, skipped, or (failed and
that step is optional). The runner never inserts rows mid-flight.
"""
from dataclasses import dataclass

_MIN = 60


@dataclass(frozen=True)
class Step:
    name: str
    requires: tuple[str, ...] = ()
    timeout_s: int = 10 * _MIN
    max_attempts: int = 3
    optional: bool = False
    gate: str | None = None


PIPELINE: list[Step] = [
    # Phase 1: analysis
    Step("ingestion"),
    Step("vision_tier1", requires=("ingestion",)),
    Step("property_verification", requires=("ingestion",), timeout_s=2 * _MIN, optional=True),
    Step("vision_tier2", requires=("vision_tier1",), timeout_s=20 * _MIN),
    Step("coverage", requires=("vision_tier2",)),
    Step("virtual_staging", requires=("coverage",), timeout_s=15 * _MIN, optional=True, gate="addon:virtual_staging"),
    Step("floorplan", requires=("coverage", "virtual_staging"), timeout_s=20 * _MIN),
    Step("dollhouse_render", requires=("floorplan",), optional=True),
    Step("packaging", requires=("floorplan", "dollhouse_render", "property_verification")),
    Step("photo_compliance", requires=("packaging",), optional=True),
    Step("video", requires=("packaging",), timeout_s=30 * _MIN, optional=True, gate="video"),
    # Human gate
    Step("await_review", requires=("packaging",), gate="review"),
    # Phase 2: post-approval
    Step("content", requires=("await_review",)),
    Step("brand", requires=("content",), optional=True),
    Step("social_content", requires=("content",), optional=True),
    Step("chapters", requires=("video", "await_review"), optional=True),
    Step("social_cuts", requires=("video", "await_review"), optional=True),
    Step("mls_export", requires=("content", "brand"), timeout_s=15 * _MIN),
    Step("distribution", requires=("mls_export", "social_content", "chapters", "social_cuts", "photo_compliance")),
    # Phase 3: after delivery, all best-effort
    Step("microsite", requires=("distribution",), timeout_s=5 * _MIN, optional=True),
    Step("learning", requires=("distribution",), optional=True),
    Step("social_event", requires=("distribution",), timeout_s=2 * _MIN, optional=True),
    Step("health_score", requires=("distribution",), timeout_s=2 * _MIN, optional=True),
    Step("performance_intelligence", requires=("distribution",), timeout_s=2 * _MIN, optional=True),
]


def validate_pipeline(steps: list[Step]) -> None:
    names = [s.name for s in steps]
    if len(names) != len(set(names)):
        raise ValueError("duplicate step names")
    known = set(names)
    for s in steps:
        for dep in s.requires:
            if dep not in known:
                raise ValueError(f"step {s.name!r} requires unknown step {dep!r}")
    topological_order(steps)  # raises on cycle


def topological_order(steps: list[Step]) -> list[str]:
    deps = {s.name: set(s.requires) for s in steps}
    order: list[str] = []
    while deps:
        ready = sorted(n for n, d in deps.items() if not d)
        if not ready:
            raise ValueError(f"cycle among steps: {sorted(deps)}")
        for n in ready:
            order.append(n)
            deps.pop(n)
        for d in deps.values():
            d.difference_update(ready)
    return order


validate_pipeline(PIPELINE)
STEP_INDEX: dict[str, Step] = {s.name: s for s in PIPELINE}
```

Note the deliberate dependency choice: `distribution` waits for the optional post-approval steps so "DELIVERED" is not announced before the bundle's social captions and cuts exist (today eleven steps run after the user is told it's delivered). Optional failures still satisfy the dependency, so a broken social step cannot block delivery.

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python.exe -m pytest tests/test_pipeline -q -p no:cacheprovider` (timeout 60000). Expected: PASS. Ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/listingjet/pipeline tests/test_pipeline
git commit -m "feat(pipeline): declarative step definition with gates and dependency validation"
```

---

### Task 3: Step callables

**Files:**
- Create: `src/listingjet/pipeline/steps.py`
- Test: `tests/test_pipeline/test_steps.py`

**Interfaces:**
- Consumes: `PIPELINE` from Task 2; agents under `src/listingjet/agents/`; `AgentContext(listing_id: str, tenant_id: str)` from `agents/base.py`.
- Produces:
  ```python
  @dataclass
  class StepContext:
      listing_id: str
      tenant_id: str
      results: dict[str, dict]        # results of already-done sibling jobs, keyed by step name
      def agent_context(self) -> AgentContext
  StepFn = Callable[[StepContext], Awaitable[dict]]
  STEP_FUNCTIONS: dict[str, StepFn]   # one entry per PIPELINE step except await_review
  ```

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pipeline/test_steps.py
import uuid
from unittest.mock import AsyncMock, patch

import pytest

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
        content_result={"mls_safe": "A", "marketing": "B"}, flyer_s3_key="flyers/x.pdf",
    )


@pytest.mark.asyncio
async def test_vision_tier1_uses_run_tier1():
    ctx = StepContext(listing_id=str(uuid.uuid4()), tenant_id=str(uuid.uuid4()), results={})
    with patch("listingjet.pipeline.steps.VisionAgent") as agent_cls:
        agent_cls.return_value.run_tier1 = AsyncMock(return_value=7)
        out = await STEP_FUNCTIONS["vision_tier1"](ctx)
    assert out == {"count": 7}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_pipeline/test_steps.py -q -p no:cacheprovider` (timeout 60000). Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement**

Port every function from `src/listingjet/activities/pipeline.py` (lines 22–137) and `activities/social_event.py` into `steps.py`, dropping the `@activity.defn` decorators and Temporal imports. Agents are imported at module top (they are already imported lazily in tests via patch targets `listingjet.pipeline.steps.<AgentClass>`).

```python
# src/listingjet/pipeline/steps.py
"""One async callable per pipeline step. Each wraps an existing agent unchanged.

Replaces activities/pipeline.py and activities/social_event.py.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from listingjet.agents.base import AgentContext
from listingjet.agents.brand import BrandAgent
from listingjet.agents.chapter import ChapterAgent
from listingjet.agents.content import ContentAgent
from listingjet.agents.coverage import CoverageAgent
from listingjet.agents.distribution import DistributionAgent
from listingjet.agents.dollhouse_render import DollhouseRenderAgent
from listingjet.agents.floorplan import FloorplanAgent
from listingjet.agents.health_score import HealthScoreAgent
from listingjet.agents.ingestion import IngestionAgent
from listingjet.agents.learning import LearningAgent
from listingjet.agents.microsite_generator import MicrositeGeneratorAgent
from listingjet.agents.mls_export import MLSExportAgent
from listingjet.agents.packaging import PackagingAgent
from listingjet.agents.performance_intelligence import PerformanceIntelligenceAgent
from listingjet.agents.photo_compliance import PhotoComplianceAgent
from listingjet.agents.property_verification import PropertyVerificationAgent
from listingjet.agents.social_content import SocialContentAgent
from listingjet.agents.social_cuts import SocialCutAgent
from listingjet.agents.video import VideoAgent
from listingjet.agents.virtual_staging import VirtualStagingAgent
from listingjet.agents.vision import VisionAgent

logger = logging.getLogger(__name__)


@dataclass
class StepContext:
    listing_id: str
    tenant_id: str
    results: dict[str, dict] = field(default_factory=dict)

    def agent_context(self) -> AgentContext:
        return AgentContext(listing_id=self.listing_id, tenant_id=self.tenant_id)


StepFn = Callable[[StepContext], Awaitable[dict]]


def _agent_step(agent_cls) -> StepFn:
    async def run(ctx: StepContext) -> dict:
        result = await agent_cls().instrumented_execute(ctx.agent_context())
        return result if isinstance(result, dict) else {"result": result}
    run.__name__ = f"run_{agent_cls.agent_name}"
    return run


async def run_vision_tier1(ctx: StepContext) -> dict:
    return {"count": await VisionAgent().run_tier1(ctx.agent_context())}


async def run_vision_tier2(ctx: StepContext) -> dict:
    return {"count": await VisionAgent().run_tier2(ctx.agent_context())}


async def run_mls_export(ctx: StepContext) -> dict:
    brand = ctx.results.get("brand") or {}
    agent = MLSExportAgent(
        content_result=ctx.results.get("content") or {},
        flyer_s3_key=brand.get("flyer_s3_key"),
    )
    return await agent.instrumented_execute(ctx.agent_context())


async def run_social_event(ctx: StepContext) -> dict:
    # Ported from activities/social_event.py; that module imported a
    # non-existent `get_async_session`, so this step has never succeeded.
    ...  # paste the body of activities/social_event.py::run_social_event here,
         # replacing `get_async_session()` with `AsyncSessionLocal()` (from listingjet.database)
         # and `context.listing_id` with `ctx.listing_id`.


STEP_FUNCTIONS: dict[str, StepFn] = {
    "ingestion": _agent_step(IngestionAgent),
    "vision_tier1": run_vision_tier1,
    "property_verification": _agent_step(PropertyVerificationAgent),
    "vision_tier2": run_vision_tier2,
    "coverage": _agent_step(CoverageAgent),
    "virtual_staging": _agent_step(VirtualStagingAgent),
    "floorplan": _agent_step(FloorplanAgent),
    "dollhouse_render": _agent_step(DollhouseRenderAgent),
    "packaging": _agent_step(PackagingAgent),
    "photo_compliance": _agent_step(PhotoComplianceAgent),
    "video": _agent_step(VideoAgent),
    "content": _agent_step(ContentAgent),
    "brand": _agent_step(BrandAgent),
    "social_content": _agent_step(SocialContentAgent),
    "chapters": _agent_step(ChapterAgent),
    "social_cuts": _agent_step(SocialCutAgent),
    "mls_export": run_mls_export,
    "distribution": _agent_step(DistributionAgent),
    "microsite": _agent_step(MicrositeGeneratorAgent),
    "learning": _agent_step(LearningAgent),
    "social_event": run_social_event,
    "health_score": _agent_step(HealthScoreAgent),
    "performance_intelligence": _agent_step(PerformanceIntelligenceAgent),
}
```

The `...` in `run_social_event` is the one place you must copy existing code: take the body of `activities/social_event.py::run_social_event` verbatim with the two substitutions named in the comment. Confirm every agent class name against `activities/pipeline.py` (some differ from the file name, e.g. `SocialCutAgent`, `MicrositeGeneratorAgent`); fix imports to match what exists.

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python.exe -m pytest tests/test_pipeline -q -p no:cacheprovider` (timeout 120000). Expected: PASS. Ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/listingjet/pipeline/steps.py tests/test_pipeline/test_steps.py
git commit -m "feat(pipeline): step callables wrapping the existing agents"
```

---

### Task 4: Runner core — enqueue, claim, run, dependents

**Files:**
- Create: `src/listingjet/pipeline/runner.py`
- Modify: `src/listingjet/pipeline/__init__.py`
- Test: `tests/test_pipeline/test_runner.py`

**Interfaces:**
- Consumes: `PipelineJob`, `JobStatus` (Task 1); `Step`, `PIPELINE`, `STEP_INDEX` (Task 2); `STEP_FUNCTIONS`, `StepContext` (Task 3).
- Produces (all in `runner.py`):
  ```python
  SATISFIED = {JobStatus.DONE, JobStatus.SKIPPED}
  async def enqueue_pipeline(session, listing, *, billing_model: str, enabled_addons: list[str], steps=PIPELINE) -> list[PipelineJob]
  async def claim_next(session, worker_id: str, *, steps=PIPELINE) -> PipelineJob | None
  async def run_job(session_factory, job_id, *, steps=PIPELINE, functions=STEP_FUNCTIONS) -> JobStatus
  def is_satisfied(dep_job: PipelineJob | None, dep_step: Step) -> bool
  ```
  `enqueue_pipeline` inserts one row per step: `waiting` for `gate="review"`, `skipped` for gated-off steps, `queued` otherwise; it is idempotent per listing (existing rows are left alone and returned). `claim_next` returns a job it has already marked `running` and committed. `run_job` executes the step function, stores `result`, marks `done` (`finished_at` set); the failure path is Task 5.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pipeline/test_runner.py
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from listingjet.models.listing import Listing, ListingState
from listingjet.models.pipeline_job import JobStatus, PipelineJob
from listingjet.pipeline.definition import Step
from listingjet.pipeline import runner
from tests.test_agents.conftest import make_session_factory

# A tiny pipeline for runner tests: a -> b -> gate -> c ; opt (optional) -> c ; skip (gated off)
STEPS = [
    Step("a"),
    Step("b", requires=("a",)),
    Step("opt", requires=("a",), optional=True, max_attempts=2),
    Step("skip", requires=("a",), gate="addon:never"),
    Step("gate", requires=("b",), gate="review"),
    Step("c", requires=("gate", "opt", "skip")),
]


async def _listing(db_session) -> Listing:
    obj = Listing(tenant_id=uuid.uuid4(), address={"street": "1 Test St"}, metadata_={},
                  state=ListingState.UPLOADING)
    db_session.add(obj)
    await db_session.flush()
    return obj


async def _jobs(db_session, listing_id) -> dict[str, PipelineJob]:
    rows = (await db_session.execute(
        select(PipelineJob).where(PipelineJob.listing_id == listing_id))).scalars().all()
    return {j.step: j for j in rows}


@pytest.mark.asyncio
async def test_enqueue_creates_one_row_per_step_with_gates_applied(db_session):
    listing = await _listing(db_session)
    created = await runner.enqueue_pipeline(
        db_session, listing, billing_model="legacy", enabled_addons=[], steps=STEPS)
    assert len(created) == 6
    jobs = await _jobs(db_session, listing.id)
    assert jobs["a"].status == JobStatus.QUEUED
    assert jobs["gate"].status == JobStatus.WAITING
    assert jobs["skip"].status == JobStatus.SKIPPED
    assert jobs["opt"].max_attempts == 2
    # idempotent
    again = await runner.enqueue_pipeline(
        db_session, listing, billing_model="legacy", enabled_addons=[], steps=STEPS)
    assert {j.id for j in again} == {j.id for j in created}


@pytest.mark.asyncio
async def test_claim_respects_dependencies_and_marks_running(db_session):
    listing = await _listing(db_session)
    await runner.enqueue_pipeline(db_session, listing, billing_model="legacy", enabled_addons=[], steps=STEPS)
    job = await runner.claim_next(db_session, "w1", steps=STEPS)
    assert job is not None and job.step == "a"
    assert job.status == JobStatus.RUNNING and job.locked_by == "w1" and job.locked_at is not None
    # b/opt are blocked on a, which is running, so nothing else is claimable
    assert await runner.claim_next(db_session, "w2", steps=STEPS) is None


@pytest.mark.asyncio
async def test_run_job_success_stores_result_and_unblocks_dependents(db_session):
    listing = await _listing(db_session)
    await runner.enqueue_pipeline(db_session, listing, billing_model="legacy", enabled_addons=[], steps=STEPS)
    calls: list[str] = []

    async def fn_a(ctx):
        calls.append("a")
        return {"n": 1}

    async def fn_b(ctx):
        calls.append("b")
        assert ctx.results["a"] == {"n": 1}
        return {"n": 2}

    functions = {"a": fn_a, "b": fn_b, "opt": fn_a, "c": fn_a}
    factory = make_session_factory(db_session)

    job = await runner.claim_next(db_session, "w1", steps=STEPS)
    assert await runner.run_job(factory, job.id, steps=STEPS, functions=functions) == JobStatus.DONE
    jobs = await _jobs(db_session, listing.id)
    assert jobs["a"].status == JobStatus.DONE and jobs["a"].result == {"n": 1}
    assert jobs["a"].finished_at is not None

    nxt = await runner.claim_next(db_session, "w1", steps=STEPS)
    assert nxt.step in ("b", "opt")
    await runner.run_job(factory, nxt.id, steps=STEPS, functions=functions)
    assert calls[:2] == ["a", nxt.step]


def test_is_satisfied_rules():
    step = Step("x", optional=True)
    req = Step("y")
    assert runner.is_satisfied(None, req) is False
    for status, expected in [(JobStatus.DONE, True), (JobStatus.SKIPPED, True),
                             (JobStatus.QUEUED, False), (JobStatus.RUNNING, False)]:
        assert runner.is_satisfied(PipelineJob(step="y", status=status), req) is expected
    assert runner.is_satisfied(PipelineJob(step="x", status=JobStatus.FAILED), step) is True
    assert runner.is_satisfied(PipelineJob(step="y", status=JobStatus.FAILED), req) is False
```

Check `tests/conftest.py`'s `db_session` fixture: if it wraps each test in a transaction/savepoint, `FOR UPDATE SKIP LOCKED` works inside it (the outbox poller already relies on that with a fallback). `run_job` commits through the factory; with `make_session_factory(db_session)` the "commit" is on the shared test session, which is what these tests want.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_pipeline/test_runner.py -q -p no:cacheprovider` (timeout 120000). Expected: ImportError on `runner`.

- [ ] **Step 3: Implement the core**

```python
# src/listingjet/pipeline/runner.py
"""Job-table pipeline runner. See docs/superpowers/specs/2026-09-05-free-tier-rework-design.md (Phase 2)."""
from __future__ import annotations

import asyncio
import logging
import socket
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.listing import Listing, ListingState
from listingjet.models.pipeline_job import JobStatus, PipelineJob
from listingjet.pipeline.definition import PIPELINE, Step
from listingjet.pipeline.steps import STEP_FUNCTIONS, StepContext

logger = logging.getLogger(__name__)

SATISFIED = {JobStatus.DONE, JobStatus.SKIPPED}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _gated_off(step: Step, billing_model: str, enabled_addons: list[str]) -> bool:
    if step.gate is None or step.gate == "review":
        return False
    if step.gate.startswith("addon:"):
        return step.gate.removeprefix("addon:") not in enabled_addons
    if step.gate == "video":
        return billing_model == "credit" and "ai_video_tour" not in enabled_addons
    raise ValueError(f"unknown gate {step.gate!r} on step {step.name}")


async def enqueue_pipeline(
    session: AsyncSession,
    listing: Listing,
    *,
    billing_model: str,
    enabled_addons: list[str],
    steps: list[Step] = PIPELINE,
) -> list[PipelineJob]:
    existing = {
        j.step: j for j in (await session.execute(
            select(PipelineJob).where(PipelineJob.listing_id == listing.id))).scalars().all()
    }
    jobs: list[PipelineJob] = []
    for step in steps:
        if step.name in existing:
            jobs.append(existing[step.name])
            continue
        if step.gate == "review":
            status = JobStatus.WAITING
        elif _gated_off(step, billing_model, enabled_addons):
            status = JobStatus.SKIPPED
        else:
            status = JobStatus.QUEUED
        job = PipelineJob(
            tenant_id=listing.tenant_id, listing_id=listing.id, step=step.name,
            status=status, max_attempts=step.max_attempts, run_after=_now(),
            payload={"billing_model": billing_model, "enabled_addons": enabled_addons},
        )
        session.add(job)
        jobs.append(job)
    await session.flush()
    return jobs


def is_satisfied(dep_job: PipelineJob | None, dep_step: Step) -> bool:
    if dep_job is None:
        return False
    if dep_job.status in SATISFIED:
        return True
    return dep_job.status == JobStatus.FAILED and dep_step.optional


async def _siblings(session: AsyncSession, listing_id) -> dict[str, PipelineJob]:
    rows = (await session.execute(
        select(PipelineJob).where(PipelineJob.listing_id == listing_id))).scalars().all()
    return {j.step: j for j in rows}


async def claim_next(session: AsyncSession, worker_id: str, *, steps: list[Step] = PIPELINE) -> PipelineJob | None:
    """Claim the oldest runnable job. Marks it RUNNING and commits before returning."""
    index = {s.name: s for s in steps}
    candidates = (await session.execute(
        select(PipelineJob)
        .where(PipelineJob.status == JobStatus.QUEUED, PipelineJob.run_after <= _now())
        .order_by(PipelineJob.run_after, PipelineJob.created_at)
        .limit(50)
        .with_for_update(skip_locked=True)
    )).scalars().all()
    sibling_cache: dict = {}
    for job in candidates:
        step = index.get(job.step)
        if step is None:
            continue
        if job.listing_id not in sibling_cache:
            sibling_cache[job.listing_id] = await _siblings(session, job.listing_id)
        sibs = sibling_cache[job.listing_id]
        if all(is_satisfied(sibs.get(dep), index[dep]) for dep in step.requires):
            job.status = JobStatus.RUNNING
            job.locked_by = worker_id
            job.locked_at = _now()
            job.started_at = _now()
            job.attempts += 1
            await session.commit()
            return job
    await session.commit()  # release the row locks
    return None


async def run_job(session_factory, job_id, *, steps: list[Step] = PIPELINE, functions=STEP_FUNCTIONS) -> JobStatus:
    index = {s.name: s for s in steps}
    async with session_factory() as session:
        job = await session.get(PipelineJob, job_id)
        step = index[job.step]
        sibs = await _siblings(session, job.listing_id)
        results = {name: j.result for name, j in sibs.items() if j.status == JobStatus.DONE and j.result is not None}
        ctx = StepContext(listing_id=str(job.listing_id), tenant_id=str(job.tenant_id), results=results)
        fn = functions[job.step]
    try:
        result = await asyncio.wait_for(fn(ctx), timeout=step.timeout_s)
    except Exception as exc:  # noqa: BLE001 — every failure is classified in _handle_failure (Task 5)
        return await _handle_failure(session_factory, job_id, step, exc)
    async with session_factory() as session:
        job = await session.get(PipelineJob, job_id)
        job.status = JobStatus.DONE
        job.result = result if isinstance(result, dict) else {"result": result}
        job.error = None
        job.finished_at = _now()
        job.locked_by = None
        await session.commit()
    logger.info("pipeline.step.done listing=%s step=%s", job.listing_id, job.step)
    return JobStatus.DONE


async def _handle_failure(session_factory, job_id, step: Step, exc: BaseException) -> JobStatus:
    raise NotImplementedError  # Task 5
```

`src/listingjet/pipeline/__init__.py`:

```python
from listingjet.pipeline.definition import PIPELINE, STEP_INDEX, Step  # noqa: F401
from listingjet.pipeline.runner import enqueue_pipeline  # noqa: F401
```

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python.exe -m pytest tests/test_pipeline -q -p no:cacheprovider` (timeout 120000). Expected: PASS. Ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/listingjet/pipeline tests/test_pipeline/test_runner.py
git commit -m "feat(pipeline): runner core — enqueue, SKIP LOCKED claim, run, dependency resolution"
```

---

### Task 5: Failure handling — retry with backoff, non-retryable errors, optional vs required, timeouts, stale reclaim

**Files:**
- Modify: `src/listingjet/pipeline/runner.py`
- Test: `tests/test_pipeline/test_runner_failures.py`

**Interfaces:**
- Produces:
  ```python
  def is_retryable(exc: BaseException) -> bool
  def backoff_seconds(attempt: int) -> int          # 30, 60, 120, ... capped at 600
  async def _handle_failure(session_factory, job_id, step, exc) -> JobStatus
  async def fail_listing(session, listing_id, *, step: str, error: str) -> None
  async def reclaim_stale(session, *, steps=PIPELINE) -> int
  ```
  Rules: `asyncio.TimeoutError`, connection errors, HTTP 5xx and 429 are retryable; `ValueError`, `KeyError`, `TypeError`, `PermissionError`, HTTP 4xx (other than 429), and `anthropic.BadRequestError` are not. A retryable failure with attempts left → `queued` with `run_after = now + backoff`. Otherwise `failed`. A `failed` non-optional step → `fail_listing`: `Listing.state = FAILED`, every sibling in `queued`/`waiting` → `cancelled`, and an `Event` `pipeline.failed` with `{step, error}` via `services.events.emit_event`. `reclaim_stale` resets `running` jobs whose `locked_at < now - 2*timeout_s` back to `queued` (attempt already counted by `claim_next`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pipeline/test_runner_failures.py
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import select

from listingjet.models.event import Event
from listingjet.models.listing import Listing, ListingState
from listingjet.models.pipeline_job import JobStatus, PipelineJob
from listingjet.pipeline import runner
from listingjet.pipeline.definition import Step
from tests.test_agents.conftest import make_session_factory

STEPS = [Step("a", max_attempts=2, timeout_s=1), Step("opt", requires=("a",), optional=True, max_attempts=1),
         Step("b", requires=("a",)), Step("c", requires=("b", "opt"))]


async def _setup(db_session):
    listing = Listing(tenant_id=uuid.uuid4(), address={"street": "1 Fail St"}, metadata_={},
                      state=ListingState.ANALYZING)
    db_session.add(listing)
    await db_session.flush()
    await runner.enqueue_pipeline(db_session, listing, billing_model="legacy", enabled_addons=[], steps=STEPS)
    return listing, make_session_factory(db_session)


async def _job(db_session, listing_id, step):
    return (await db_session.execute(select(PipelineJob).where(
        PipelineJob.listing_id == listing_id, PipelineJob.step == step))).scalar_one()


def test_is_retryable_classification():
    assert runner.is_retryable(asyncio.TimeoutError()) is True
    assert runner.is_retryable(ConnectionError()) is True
    req = httpx.Request("GET", "http://x")
    assert runner.is_retryable(httpx.HTTPStatusError("x", request=req, response=httpx.Response(503, request=req))) is True
    assert runner.is_retryable(httpx.HTTPStatusError("x", request=req, response=httpx.Response(429, request=req))) is True
    assert runner.is_retryable(httpx.HTTPStatusError("x", request=req, response=httpx.Response(400, request=req))) is False
    assert runner.is_retryable(ValueError("Listing not found")) is False
    assert runner.is_retryable(RuntimeError("boom")) is True


def test_backoff_grows_and_caps():
    assert [runner.backoff_seconds(n) for n in (1, 2, 3, 6)] == [30, 60, 120, 600]


@pytest.mark.asyncio
async def test_retryable_failure_requeues_with_backoff(db_session):
    listing, factory = await _setup(db_session)

    async def boom(ctx):
        raise RuntimeError("transient")

    job = await runner.claim_next(db_session, "w", steps=STEPS)
    status = await runner.run_job(factory, job.id, steps=STEPS, functions={"a": boom})
    assert status == JobStatus.QUEUED
    j = await _job(db_session, listing.id, "a")
    assert j.attempts == 1 and "transient" in j.error
    assert j.run_after > datetime.now(timezone.utc) + timedelta(seconds=20)
    assert (await db_session.get(Listing, listing.id)).state == ListingState.ANALYZING


@pytest.mark.asyncio
async def test_non_retryable_failure_fails_listing_and_cancels_rest(db_session):
    listing, factory = await _setup(db_session)

    async def bad(ctx):
        raise ValueError("Listing not found")

    job = await runner.claim_next(db_session, "w", steps=STEPS)
    status = await runner.run_job(factory, job.id, steps=STEPS, functions={"a": bad})
    assert status == JobStatus.FAILED
    jobs = {j.step: j for j in (await db_session.execute(
        select(PipelineJob).where(PipelineJob.listing_id == listing.id))).scalars().all()}
    assert jobs["a"].status == JobStatus.FAILED and jobs["a"].attempts == 1
    assert {jobs[s].status for s in ("opt", "b", "c")} == {JobStatus.CANCELLED}
    assert (await db_session.get(Listing, listing.id)).state == ListingState.FAILED
    evt = (await db_session.execute(select(Event).where(
        Event.listing_id == listing.id, Event.event_type == "pipeline.failed"))).scalar_one()
    assert evt.payload["step"] == "a" and "Listing not found" in evt.payload["error"]


@pytest.mark.asyncio
async def test_optional_failure_does_not_fail_listing(db_session):
    listing, factory = await _setup(db_session)

    async def ok(ctx):
        return {}

    async def bad(ctx):
        raise ValueError("no")

    fns = {"a": ok, "opt": bad, "b": ok, "c": ok}
    for _ in range(2):  # a, then opt (or b)
        job = await runner.claim_next(db_session, "w", steps=STEPS)
        await runner.run_job(factory, job.id, steps=STEPS, functions=fns)
    # drain remaining
    while (job := await runner.claim_next(db_session, "w", steps=STEPS)) is not None:
        await runner.run_job(factory, job.id, steps=STEPS, functions=fns)
    jobs = {j.step: j for j in (await db_session.execute(
        select(PipelineJob).where(PipelineJob.listing_id == listing.id))).scalars().all()}
    assert jobs["opt"].status == JobStatus.FAILED
    assert jobs["c"].status == JobStatus.DONE
    assert (await db_session.get(Listing, listing.id)).state == ListingState.ANALYZING


@pytest.mark.asyncio
async def test_timeout_is_retryable(db_session):
    listing, factory = await _setup(db_session)

    async def slow(ctx):
        await asyncio.sleep(5)

    job = await runner.claim_next(db_session, "w", steps=STEPS)
    assert await runner.run_job(factory, job.id, steps=STEPS, functions={"a": slow}) == JobStatus.QUEUED
    assert "timed out" in (await _job(db_session, listing.id, "a")).error


@pytest.mark.asyncio
async def test_reclaim_stale_running_jobs(db_session):
    listing, factory = await _setup(db_session)
    job = await runner.claim_next(db_session, "w", steps=STEPS)
    job.locked_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.flush()
    assert await runner.reclaim_stale(db_session, steps=STEPS) == 1
    j = await _job(db_session, listing.id, "a")
    assert j.status == JobStatus.QUEUED and j.locked_by is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_pipeline/test_runner_failures.py -q -p no:cacheprovider` (timeout 120000). Expected: AttributeError / NotImplementedError.

- [ ] **Step 3: Implement**

Replace the `_handle_failure` stub in `runner.py` and add the helpers:

```python
import httpx

_NON_RETRYABLE = (ValueError, KeyError, TypeError, PermissionError, NotImplementedError)


def is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, asyncio.TimeoutError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code == 429 or code >= 500
    try:
        import anthropic
        if isinstance(exc, anthropic.BadRequestError):
            return False
        if isinstance(exc, (anthropic.RateLimitError, anthropic.APIConnectionError)):
            return True
    except ImportError:
        pass
    if isinstance(exc, _NON_RETRYABLE):
        return False
    return True


def backoff_seconds(attempt: int) -> int:
    return min(600, 30 * (2 ** (attempt - 1)))


def _describe(exc: BaseException) -> str:
    if isinstance(exc, asyncio.TimeoutError):
        return "step timed out"
    return f"{type(exc).__name__}: {exc}"[:2000]


async def fail_listing(session: AsyncSession, listing_id, *, step: str, error: str) -> None:
    from listingjet.services.events import emit_event

    listing = await session.get(Listing, listing_id)
    if listing is None:
        return
    listing.state = ListingState.FAILED
    await session.execute(
        update(PipelineJob)
        .where(PipelineJob.listing_id == listing_id,
               PipelineJob.status.in_([JobStatus.QUEUED, JobStatus.WAITING]))
        .values(status=JobStatus.CANCELLED)
    )
    await emit_event(session=session, event_type="pipeline.failed",
                     payload={"step": step, "error": error},
                     tenant_id=str(listing.tenant_id), listing_id=str(listing_id))


async def _handle_failure(session_factory, job_id, step: Step, exc: BaseException) -> JobStatus:
    error = _describe(exc)
    logger.warning("pipeline.step.failed step=%s job=%s error=%s", step.name, job_id, error,
                   exc_info=not isinstance(exc, asyncio.TimeoutError))
    async with session_factory() as session:
        job = await session.get(PipelineJob, job_id)
        job.error = error
        job.locked_by = None
        if is_retryable(exc) and job.attempts < job.max_attempts:
            job.status = JobStatus.QUEUED
            job.run_after = _now() + timedelta(seconds=backoff_seconds(job.attempts))
            await session.commit()
            return JobStatus.QUEUED
        job.status = JobStatus.FAILED
        job.finished_at = _now()
        if not step.optional:
            await fail_listing(session, job.listing_id, step=step.name, error=error)
        await session.commit()
        return JobStatus.FAILED


async def reclaim_stale(session: AsyncSession, *, steps: list[Step] = PIPELINE) -> int:
    index = {s.name: s for s in steps}
    rows = (await session.execute(
        select(PipelineJob).where(PipelineJob.status == JobStatus.RUNNING).with_for_update(skip_locked=True)
    )).scalars().all()
    reclaimed = 0
    now = _now()
    for job in rows:
        step = index.get(job.step)
        limit = timedelta(seconds=2 * (step.timeout_s if step else 600))
        if job.locked_at and job.locked_at < now - limit:
            job.status = JobStatus.QUEUED
            job.locked_by = None
            job.error = "reclaimed after worker died"
            reclaimed += 1
    await session.flush()
    return reclaimed
```

Also change `run_job`'s `except Exception` block to `except (Exception, asyncio.CancelledError)` only if you observe cancellation leaking during tests; otherwise leave it.

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python.exe -m pytest tests/test_pipeline -q -p no:cacheprovider` (timeout 120000). Expected: PASS. Ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/listingjet/pipeline/runner.py tests/test_pipeline/test_runner_failures.py
git commit -m "feat(pipeline): retry with backoff, non-retryable errors, listing failure, stale reclaim"
```

---

### Task 6: Review gate, auto-approve, retry and cancel helpers

**Files:**
- Modify: `src/listingjet/pipeline/runner.py`, `src/listingjet/pipeline/__init__.py`
- Test: `tests/test_pipeline/test_runner_control.py`

**Interfaces:**
- Produces:
  ```python
  async def complete_review(session, listing_id) -> bool      # waiting -> done; False if no waiting gate
  async def retry_listing(session, listing, *, steps=PIPELINE) -> int   # failed/cancelled -> queued; returns count
  async def cancel_listing_jobs(session, listing_id) -> int   # queued/waiting/running -> cancelled
  async def listing_progress(session, listing_id, *, steps=PIPELINE) -> list[dict]  # for the status endpoint
  ```
  Auto-approve: after a `packaging` job finishes `done` with `result["auto_approved"] is True`, `run_job` marks the listing's `await_review` gate `done` itself (so no human action is needed). `retry_listing` also resets `Listing.state`: `UPLOADING` if `ingestion` is not done, else `ANALYZING` if `packaging` is not done, else leaves the state alone; if the listing has no jobs at all it enqueues a fresh pipeline (needs `billing_model`/`enabled_addons`, so it takes them as keyword args with defaults `"legacy"`, `[]`). `listing_progress` returns, in `PIPELINE` order, `{"name", "status", "completed_at", "progress": None, "error", "attempts"}` with status mapped: queued/waiting → `pending`, running → `in_progress`, done → `completed`, failed → `failed`, skipped/cancelled → `skipped`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pipeline/test_runner_control.py
import uuid

import pytest
from sqlalchemy import select

from listingjet.models.listing import Listing, ListingState
from listingjet.models.pipeline_job import JobStatus, PipelineJob
from listingjet.pipeline import runner
from listingjet.pipeline.definition import Step
from tests.test_agents.conftest import make_session_factory

STEPS = [Step("ingestion"), Step("packaging", requires=("ingestion",)),
         Step("await_review", requires=("packaging",), gate="review"),
         Step("content", requires=("await_review",))]


async def _setup(db_session, state=ListingState.UPLOADING):
    listing = Listing(tenant_id=uuid.uuid4(), address={"street": "1 Gate St"}, metadata_={}, state=state)
    db_session.add(listing)
    await db_session.flush()
    await runner.enqueue_pipeline(db_session, listing, billing_model="legacy", enabled_addons=[], steps=STEPS)
    return listing, make_session_factory(db_session)


async def _status(db_session, listing_id, step):
    return (await db_session.execute(select(PipelineJob.status).where(
        PipelineJob.listing_id == listing_id, PipelineJob.step == step))).scalar_one()


@pytest.mark.asyncio
async def test_complete_review_unblocks_content(db_session):
    listing, factory = await _setup(db_session)
    ok = {"ingestion": lambda ctx: _ret({}), "packaging": lambda ctx: _ret({"auto_approved": False}),
          "content": lambda ctx: _ret({})}
    for _ in range(2):
        job = await runner.claim_next(db_session, "w", steps=STEPS)
        await runner.run_job(factory, job.id, steps=STEPS, functions=ok)
    assert await runner.claim_next(db_session, "w", steps=STEPS) is None  # blocked on the gate
    assert await runner.complete_review(db_session, listing.id) is True
    assert await _status(db_session, listing.id, "await_review") == JobStatus.DONE
    assert (await runner.claim_next(db_session, "w", steps=STEPS)).step == "content"
    assert await runner.complete_review(db_session, listing.id) is False


@pytest.mark.asyncio
async def test_packaging_auto_approve_completes_gate(db_session):
    listing, factory = await _setup(db_session)
    fns = {"ingestion": lambda ctx: _ret({}), "packaging": lambda ctx: _ret({"auto_approved": True})}
    for _ in range(2):
        job = await runner.claim_next(db_session, "w", steps=STEPS)
        await runner.run_job(factory, job.id, steps=STEPS, functions=fns)
    assert await _status(db_session, listing.id, "await_review") == JobStatus.DONE


@pytest.mark.asyncio
async def test_retry_listing_requeues_failed_and_cancelled(db_session):
    listing, factory = await _setup(db_session)
    job = await runner.claim_next(db_session, "w", steps=STEPS)
    await runner.run_job(factory, job.id, steps=STEPS, functions={"ingestion": lambda ctx: _raise(ValueError("x"))})
    assert (await db_session.get(Listing, listing.id)).state == ListingState.FAILED
    n = await runner.retry_listing(db_session, listing, steps=STEPS)
    assert n == 3  # ingestion (failed) + packaging + content (cancelled); the gate goes back to waiting
    assert await _status(db_session, listing.id, "ingestion") == JobStatus.QUEUED
    assert await _status(db_session, listing.id, "await_review") == JobStatus.WAITING
    assert (await db_session.get(Listing, listing.id)).state == ListingState.UPLOADING


@pytest.mark.asyncio
async def test_cancel_listing_jobs(db_session):
    listing, _ = await _setup(db_session)
    assert await runner.cancel_listing_jobs(db_session, listing.id) == 4
    assert await _status(db_session, listing.id, "content") == JobStatus.CANCELLED


@pytest.mark.asyncio
async def test_listing_progress_shape(db_session):
    listing, factory = await _setup(db_session)
    job = await runner.claim_next(db_session, "w", steps=STEPS)
    await runner.run_job(factory, job.id, steps=STEPS, functions={"ingestion": lambda ctx: _ret({})})
    rows = await runner.listing_progress(db_session, listing.id, steps=STEPS)
    assert [r["name"] for r in rows] == ["ingestion", "packaging", "await_review", "content"]
    assert rows[0]["status"] == "completed" and rows[0]["completed_at"] is not None
    assert rows[1]["status"] == "pending" and rows[1]["error"] is None
    assert set(rows[0]) == {"name", "status", "completed_at", "progress", "error", "attempts"}


async def _ret(v):
    return v


async def _raise(exc):
    raise exc
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_pipeline/test_runner_control.py -q -p no:cacheprovider` (timeout 120000). Expected: AttributeError on `complete_review`.

- [ ] **Step 3: Implement**

Add to `runner.py`:

```python
_STATUS_LABEL = {
    JobStatus.QUEUED: "pending", JobStatus.WAITING: "pending", JobStatus.RUNNING: "in_progress",
    JobStatus.DONE: "completed", JobStatus.FAILED: "failed",
    JobStatus.SKIPPED: "skipped", JobStatus.CANCELLED: "skipped",
}


async def complete_review(session: AsyncSession, listing_id) -> bool:
    res = await session.execute(
        update(PipelineJob)
        .where(PipelineJob.listing_id == listing_id, PipelineJob.step == "await_review",
               PipelineJob.status == JobStatus.WAITING)
        .values(status=JobStatus.DONE, finished_at=_now(), result={"approved": True})
    )
    await session.flush()
    return res.rowcount == 1


async def retry_listing(session: AsyncSession, listing: Listing, *, steps: list[Step] = PIPELINE,
                        billing_model: str = "legacy", enabled_addons: list[str] | None = None) -> int:
    sibs = await _siblings(session, listing.id)
    if not sibs:
        created = await enqueue_pipeline(session, listing, billing_model=billing_model,
                                         enabled_addons=enabled_addons or [], steps=steps)
        listing.state = ListingState.UPLOADING
        return len(created)
    index = {s.name: s for s in steps}
    n = 0
    for job in sibs.values():
        if job.status in (JobStatus.FAILED, JobStatus.CANCELLED):
            step = index.get(job.step)
            job.status = JobStatus.WAITING if step and step.gate == "review" else JobStatus.QUEUED
            job.attempts = 0
            job.error = None
            job.locked_by = None
            job.run_after = _now()
            n += 1
    def _done(name: str) -> bool:
        j = sibs.get(name)
        return j is not None and j.status in SATISFIED
    if not _done("ingestion"):
        listing.state = ListingState.UPLOADING
    elif not _done("packaging"):
        listing.state = ListingState.ANALYZING
    await session.flush()
    return n


async def cancel_listing_jobs(session: AsyncSession, listing_id) -> int:
    res = await session.execute(
        update(PipelineJob)
        .where(PipelineJob.listing_id == listing_id,
               PipelineJob.status.in_([JobStatus.QUEUED, JobStatus.WAITING, JobStatus.RUNNING]))
        .values(status=JobStatus.CANCELLED, locked_by=None)
    )
    await session.flush()
    return res.rowcount


async def listing_progress(session: AsyncSession, listing_id, *, steps: list[Step] = PIPELINE) -> list[dict]:
    sibs = await _siblings(session, listing_id)
    rows = []
    for step in steps:
        j = sibs.get(step.name)
        if j is None:
            continue
        rows.append({
            "name": step.name,
            "status": _STATUS_LABEL[j.status],
            "completed_at": j.finished_at.isoformat() if j.finished_at and j.status == JobStatus.DONE else None,
            "progress": None,
            "error": j.error if j.status == JobStatus.FAILED else None,
            "attempts": j.attempts,
        })
    return rows
```

In `run_job`, after marking a job `done`, add the auto-approve hook (inside the same session, before `commit`):

```python
        if job.step == "packaging" and isinstance(job.result, dict) and job.result.get("auto_approved") is True:
            await complete_review(session, job.listing_id)
```

Export `complete_review`, `retry_listing`, `cancel_listing_jobs`, `listing_progress` from `pipeline/__init__.py`.

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python.exe -m pytest tests/test_pipeline -q -p no:cacheprovider` (timeout 120000). Expected: PASS. Ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/listingjet/pipeline tests/test_pipeline/test_runner_control.py
git commit -m "feat(pipeline): review gate, auto-approve, retry, cancel, progress helpers"
```

---

### Task 7: Worker loop, periodic tasks, standalone entry, lifespan wiring

**Files:**
- Modify: `src/listingjet/pipeline/runner.py` (add `worker_loop`, `periodic_loop`, `WORKER_STATE`)
- Create: `src/listingjet/pipeline/worker.py`
- Modify: `src/listingjet/config/__init__.py` (add `worker_enabled: bool = True`, `worker_concurrency: int = 2`, `worker_poll_interval_s: float = 2.0`)
- Modify: `src/listingjet/main.py` lifespan (start/stop the loops)
- Modify: `docker/entrypoint.sh` (`worker` case)
- Test: `tests/test_pipeline/test_worker.py`

**Interfaces:**
- Produces:
  ```python
  WORKER_STATE = {"last_tick": None, "worker_id": None}     # read by /health/deep
  async def worker_loop(session_factory, *, stop: asyncio.Event, concurrency: int, poll_interval_s: float, steps=PIPELINE, functions=STEP_FUNCTIONS, max_ticks: int | None = None) -> None
  async def periodic_loop(session_factory, *, stop: asyncio.Event) -> None
  ```
  `worker_loop`: each tick reclaims stale jobs, then claims up to `concurrency` jobs (a semaphore bounds in-flight `run_job` tasks), sleeps `poll_interval_s` when nothing was claimed, updates `WORKER_STATE["last_tick"]`. `max_ticks` exists for tests. `periodic_loop`: hourly `cleanup_expired_demos(session, storage=get_storage())`; weekly `run_baseline_aggregation()` (ported from `workflows/baseline_aggregation.py` into `pipeline/periodic.py`); both persist their last-run time in memory only (a restart runs them again, which is harmless).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pipeline/test_worker.py
import asyncio
import uuid

import pytest
from sqlalchemy import select

from listingjet.config import Settings
from listingjet.models.listing import Listing, ListingState
from listingjet.models.pipeline_job import JobStatus, PipelineJob
from listingjet.pipeline import runner
from listingjet.pipeline.definition import Step
from tests.test_agents.conftest import make_session_factory

STEPS = [Step("a"), Step("b", requires=("a",)), Step("c", requires=("a",))]


def test_worker_settings_defaults():
    f = Settings.model_fields
    assert f["worker_enabled"].default is True
    assert f["worker_concurrency"].default == 2
    assert f["worker_poll_interval_s"].default == 2.0


@pytest.mark.asyncio
async def test_worker_loop_drains_pipeline_with_bounded_concurrency(db_session):
    listing = Listing(tenant_id=uuid.uuid4(), address={"street": "1 Loop St"}, metadata_={},
                      state=ListingState.UPLOADING)
    db_session.add(listing)
    await db_session.flush()
    await runner.enqueue_pipeline(db_session, listing, billing_model="legacy", enabled_addons=[], steps=STEPS)

    in_flight = 0
    peak = 0

    async def fn(ctx):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.05)
        in_flight -= 1
        return {}

    stop = asyncio.Event()
    await runner.worker_loop(make_session_factory(db_session), stop=stop, concurrency=1,
                             poll_interval_s=0.01, steps=STEPS,
                             functions={"a": fn, "b": fn, "c": fn}, max_ticks=20)
    statuses = {j.step: j.status for j in (await db_session.execute(
        select(PipelineJob).where(PipelineJob.listing_id == listing.id))).scalars().all()}
    assert statuses == {"a": JobStatus.DONE, "b": JobStatus.DONE, "c": JobStatus.DONE}
    assert peak == 1
    assert runner.WORKER_STATE["last_tick"] is not None


@pytest.mark.asyncio
async def test_worker_loop_stops_on_event(db_session):
    stop = asyncio.Event()
    stop.set()
    await asyncio.wait_for(
        runner.worker_loop(make_session_factory(db_session), stop=stop, concurrency=1,
                           poll_interval_s=0.01, steps=STEPS, functions={}),
        timeout=2,
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_pipeline/test_worker.py -q -p no:cacheprovider` (timeout 120000). Expected: KeyError on settings / AttributeError on `worker_loop`.

- [ ] **Step 3: Implement**

`config/__init__.py`, near the Temporal block (which Task 9 deletes):

```python
    # Pipeline worker (runs inside the API process unless worker_enabled=false)
    worker_enabled: bool = True
    worker_concurrency: int = 2
    worker_poll_interval_s: float = 2.0
```

`runner.py`:

```python
WORKER_STATE: dict = {"last_tick": None, "worker_id": None}


async def worker_loop(session_factory, *, stop: asyncio.Event, concurrency: int, poll_interval_s: float,
                      steps: list[Step] = PIPELINE, functions=STEP_FUNCTIONS, max_ticks: int | None = None) -> None:
    worker_id = f"{socket.gethostname()}:{uuid.uuid4().hex[:8]}"
    WORKER_STATE["worker_id"] = worker_id
    sem = asyncio.Semaphore(concurrency)
    tasks: set[asyncio.Task] = set()
    ticks = 0

    async def _run(job_id):
        async with sem:
            try:
                await run_job(session_factory, job_id, steps=steps, functions=functions)
            except Exception:  # noqa: BLE001 — never let one job kill the loop
                logger.exception("pipeline.run_job crashed job=%s", job_id)

    while not stop.is_set():
        ticks += 1
        WORKER_STATE["last_tick"] = _now()
        claimed = 0
        try:
            async with session_factory() as session:
                await reclaim_stale(session, steps=steps)
                await session.commit()
            while sem._value > 0 and not stop.is_set():  # only claim when a slot is free
                async with session_factory() as session:
                    job = await claim_next(session, worker_id, steps=steps)
                if job is None:
                    break
                claimed += 1
                t = asyncio.create_task(_run(job.id))
                tasks.add(t)
                t.add_done_callback(tasks.discard)
                await asyncio.sleep(0)  # let the task acquire the semaphore
        except Exception:  # noqa: BLE001
            logger.exception("pipeline.worker_loop tick failed")
        if max_ticks is not None and ticks >= max_ticks:
            break
        if claimed == 0:
            try:
                await asyncio.wait_for(stop.wait(), timeout=poll_interval_s)
            except asyncio.TimeoutError:
                pass
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
```

`sem._value` is private; if ruff or review objects, track free slots with your own counter decremented in `_run` (before `async with sem`) and incremented after. Tests must pass either way.

`pipeline/periodic.py` (new): move `run_baseline_aggregation`'s body from `workflows/baseline_aggregation.py` into `async def run_baseline_aggregation() -> dict` (no Temporal decorator), and add:

```python
async def run_demo_cleanup() -> dict:
    from listingjet.database import AsyncSessionLocal
    from listingjet.services.demo_cleanup import cleanup_expired_demos
    from listingjet.services.storage import get_storage

    async with AsyncSessionLocal() as session:
        return await cleanup_expired_demos(session, storage=get_storage())
```

`runner.py`:

```python
async def periodic_loop(session_factory, *, stop: asyncio.Event) -> None:
    from listingjet.pipeline.periodic import run_baseline_aggregation, run_demo_cleanup

    schedule = [("demo_cleanup", run_demo_cleanup, timedelta(hours=1)),
                ("baseline_aggregation", run_baseline_aggregation, timedelta(days=7))]
    last: dict[str, datetime] = {}
    while not stop.is_set():
        for name, fn, every in schedule:
            if name not in last or _now() - last[name] >= every:
                try:
                    await fn()
                except Exception:  # noqa: BLE001
                    logger.exception("periodic task failed name=%s", name)
                last[name] = _now()
        try:
            await asyncio.wait_for(stop.wait(), timeout=60)
        except asyncio.TimeoutError:
            pass
```

`main.py` lifespan, after the outbox poller block:

```python
    worker_stop = asyncio.Event()
    worker_tasks: list[asyncio.Task] = []
    if settings.worker_enabled:
        from listingjet.pipeline.runner import periodic_loop, worker_loop
        worker_tasks = [
            asyncio.create_task(worker_loop(
                AsyncSessionLocal, stop=worker_stop, concurrency=settings.worker_concurrency,
                poll_interval_s=settings.worker_poll_interval_s)),
            asyncio.create_task(periodic_loop(AsyncSessionLocal, stop=worker_stop)),
        ]
```

and in the shutdown section:

```python
    worker_stop.set()
    for t in worker_tasks:
        try:
            await asyncio.wait_for(t, timeout=30)
        except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
            t.cancel()
```

Set `WORKER_ENABLED=false` in `tests/conftest.py`'s environment before the app is imported if the loop interferes with tests (it should not, because the test DB has no queued jobs, but the loop would open connections on the dev engine — add `os.environ.setdefault("WORKER_ENABLED", "false")` at the top of `tests/conftest.py` before `from listingjet.main import app`).

`pipeline/worker.py`:

```python
"""Standalone worker: python -m listingjet.pipeline.worker
Same loops as the in-process worker in main.py, for a dedicated worker service."""
import asyncio
import logging
import signal
from pathlib import Path

from listingjet.config import settings
from listingjet.database import AsyncSessionLocal
from listingjet.pipeline.runner import periodic_loop, worker_loop

logger = logging.getLogger(__name__)
HEARTBEAT_FILE = Path("/tmp/worker-heartbeat")


async def _heartbeat(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            HEARTBEAT_FILE.touch()
        except OSError:
            pass
        try:
            await asyncio.wait_for(stop.wait(), timeout=15)
        except asyncio.TimeoutError:
            pass


async def main() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # Windows
            pass
    logger.info("pipeline worker starting concurrency=%s", settings.worker_concurrency)
    await asyncio.gather(
        worker_loop(AsyncSessionLocal, stop=stop, concurrency=settings.worker_concurrency,
                    poll_interval_s=settings.worker_poll_interval_s),
        periodic_loop(AsyncSessionLocal, stop=stop),
        _heartbeat(stop),
    )


if __name__ == "__main__":
    asyncio.run(main())
```

`docker/entrypoint.sh` `worker` case: `exec python -m listingjet.pipeline.worker` with the echo text updated.

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python.exe -m pytest tests/test_pipeline tests/test_api/test_health.py -q -p no:cacheprovider` (timeout 300000). Expected: PASS. Ruff clean. Also `.venv/Scripts/python.exe -c "import listingjet.pipeline.worker"`.

- [ ] **Step 5: Commit**

```bash
git add src/listingjet/pipeline src/listingjet/config/__init__.py src/listingjet/main.py docker/entrypoint.sh tests/conftest.py tests/test_pipeline/test_worker.py
git commit -m "feat(pipeline): worker loop, periodic tasks, standalone entry, lifespan wiring"
```

---

### Task 8: API wiring — start, approve, retry, cancel, status, health

**Files:**
- Modify: `src/listingjet/api/listings_draft.py:185-206`, `src/listingjet/api/listings_media.py:154-166`, `src/listingjet/api/admin_listings.py:145-161`, `src/listingjet/api/bulk.py:80-86`, `src/listingjet/api/listings_workflow.py` (approve, retry, cancel, pipeline-status), `src/listingjet/api/health.py:58-66`
- Create: `src/listingjet/services/pipeline_start.py`
- Modify: `src/listingjet/api/schemas/listings.py:137-147` (`PipelineStepStatus` gains `error: str | None = None`, `attempts: int = 0`)
- Modify: `tests/conftest.py` (drop the five `get_temporal_client` patches), `tests/test_api/test_assets.py:28,95`, `tests/test_integration/test_credit_lifecycle.py:308-311`, `tests/test_monitoring/test_health.py:22`
- Test: `tests/test_api/test_pipeline_control.py`

**Interfaces:**
- Consumes: `enqueue_pipeline`, `complete_review`, `retry_listing`, `cancel_listing_jobs`, `listing_progress`, `WORKER_STATE` from `listingjet.pipeline.runner`.
- Produces: `services/pipeline_start.py::start_listing_pipeline(session, listing, tenant) -> list[PipelineJob]` which loads the tenant's enabled addon slugs the way `listings_draft.py:185-190` does today (copy that query into the helper and call it from all four start sites), then calls `enqueue_pipeline(session, listing, billing_model=tenant.billing_model, enabled_addons=slugs)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_api/test_pipeline_control.py
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from listingjet.models.listing import Listing, ListingState
from listingjet.models.pipeline_job import JobStatus, PipelineJob


async def _register(client: AsyncClient) -> tuple[str, str]:
    import jwt as pyjwt
    from listingjet.config import settings
    email = f"test-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "T", "company_name": "PipeCo", "plan_tier": "free",
    })
    token = resp.json()["access_token"]
    return token, pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])["tenant_id"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.mark.asyncio
async def test_registering_assets_enqueues_pipeline_jobs(async_client, db_session):
    token, tenant_id = await _register(async_client)
    lid = (await async_client.post("/listings", json={"address": {"street": "1 Q St"}, "metadata": {}},
                                   headers=_auth(token))).json()["id"]
    resp = await async_client.post(f"/listings/{lid}/assets", json={"assets": [
        {"file_path": f"listings/{lid}/uploads/a.jpg", "file_hash": "h1"},
    ]}, headers=_auth(token))
    assert resp.status_code == 201, resp.text
    jobs = (await db_session.execute(select(PipelineJob).where(PipelineJob.listing_id == uuid.UUID(lid)))).scalars().all()
    assert {j.step for j in jobs} >= {"ingestion", "packaging", "await_review", "distribution"}
    assert next(j for j in jobs if j.step == "await_review").status == JobStatus.WAITING


@pytest.mark.asyncio
async def test_pipeline_status_reads_jobs(async_client, db_session):
    token, tenant_id = await _register(async_client)
    lid = (await async_client.post("/listings", json={"address": {"street": "2 Q St"}, "metadata": {}},
                                   headers=_auth(token))).json()["id"]
    await async_client.post(f"/listings/{lid}/assets", json={"assets": [
        {"file_path": f"listings/{lid}/uploads/a.jpg", "file_hash": "h2"}]}, headers=_auth(token))
    resp = await async_client.get(f"/listings/{lid}/pipeline-status", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["listing_id"] == lid
    names = [s["name"] for s in body["steps"]]
    assert names[0] == "ingestion" and "await_review" in names
    assert body["steps"][0]["status"] == "pending" and body["steps"][0]["error"] is None


@pytest.mark.asyncio
async def test_approve_completes_review_gate(async_client, db_session):
    token, tenant_id = await _register(async_client)
    listing = Listing(tenant_id=uuid.UUID(tenant_id), address={"street": "3 Q St"}, metadata_={},
                      state=ListingState.IN_REVIEW)
    db_session.add(listing)
    await db_session.flush()
    db_session.add(PipelineJob(tenant_id=listing.tenant_id, listing_id=listing.id, step="await_review",
                               status=JobStatus.WAITING))
    await db_session.flush()
    resp = await async_client.post(f"/listings/{listing.id}/approve", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    job = (await db_session.execute(select(PipelineJob).where(
        PipelineJob.listing_id == listing.id, PipelineJob.step == "await_review"))).scalar_one()
    assert job.status == JobStatus.DONE


@pytest.mark.asyncio
async def test_retry_requeues_failed_listing(async_client, db_session):
    token, tenant_id = await _register(async_client)
    listing = Listing(tenant_id=uuid.UUID(tenant_id), address={"street": "4 Q St"}, metadata_={},
                      state=ListingState.FAILED)
    db_session.add(listing)
    await db_session.flush()
    db_session.add(PipelineJob(tenant_id=listing.tenant_id, listing_id=listing.id, step="ingestion",
                               status=JobStatus.FAILED, attempts=3, error="boom"))
    await db_session.flush()
    resp = await async_client.post(f"/listings/{listing.id}/retry", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["state"] == "uploading"
    job = (await db_session.execute(select(PipelineJob).where(PipelineJob.listing_id == listing.id))).scalar_one()
    assert job.status == JobStatus.QUEUED and job.attempts == 0 and job.error is None


@pytest.mark.asyncio
async def test_cancel_cancels_jobs(async_client, db_session):
    token, tenant_id = await _register(async_client)
    listing = Listing(tenant_id=uuid.UUID(tenant_id), address={"street": "5 Q St"}, metadata_={},
                      state=ListingState.UPLOADING)
    db_session.add(listing)
    await db_session.flush()
    db_session.add(PipelineJob(tenant_id=listing.tenant_id, listing_id=listing.id, step="ingestion"))
    await db_session.flush()
    resp = await async_client.post(f"/listings/{listing.id}/cancel", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    job = (await db_session.execute(select(PipelineJob).where(PipelineJob.listing_id == listing.id))).scalar_one()
    assert job.status == JobStatus.CANCELLED


@pytest.mark.asyncio
async def test_deep_health_reports_worker_not_temporal(async_client):
    resp = await async_client.get("/health/deep")
    data = resp.json()
    assert "temporal" not in data
    assert "worker" in data
```

Check the exact request body `POST /listings/{id}/assets` expects in `api/schemas/listings.py` (`CreateAssetsRequest`) and adjust the two asset payloads above to match. If `db_session` and `async_client` do not share a transaction in this repo's conftest (look at how `test_assets.py` verifies DB rows), copy that file's approach for reading rows back.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api/test_pipeline_control.py -q -p no:cacheprovider` (timeout 300000). Expected: failures (jobs not created; temporal key present in health).

- [ ] **Step 3: Implement**

`src/listingjet/services/pipeline_start.py`:

```python
"""Start the listing pipeline: resolve billing gates and enqueue jobs."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.listing import Listing
from listingjet.models.pipeline_job import PipelineJob
from listingjet.models.tenant import Tenant
from listingjet.pipeline.runner import enqueue_pipeline


async def enabled_addon_slugs(session: AsyncSession, tenant_id) -> list[str]:
    # Copy the exact query listings_draft.py uses today (AddonPurchase joined to
    # AddonCatalog, active purchases only) so all start paths agree.
    ...


async def start_listing_pipeline(session: AsyncSession, listing: Listing, tenant: Tenant | None) -> list[PipelineJob]:
    billing_model = tenant.billing_model if tenant else "legacy"
    slugs = await enabled_addon_slugs(session, listing.tenant_id)
    return await enqueue_pipeline(session, listing, billing_model=billing_model, enabled_addons=slugs)
```

Replace the `...` with the addon query lifted from `listings_draft.py:185-190` (read that block first; it builds `enabled_addon_slugs`). Then:

- `listings_draft.py:191-206`: replace the Temporal block with `await start_listing_pipeline(db, listing, tenant)` followed by `await db.commit()`; keep the `except Exception` → `FAILED` + 500 shape.
- `listings_media.py:154-166` and `admin_listings.py:145-161`: same replacement (the admin path is a retry: call `retry_listing(db, listing, billing_model=..., enabled_addons=...)` instead of enqueue, then commit).
- `listings_workflow.py` approve: replace the signal try/except with `await complete_review(db, listing.id)` **before** `db.commit()` so approval and gate completion are one transaction. `bulk.py:80-86`: same, inside the loop before its commit.
- `listings_workflow.py` retry: replace the Temporal call with `await retry_listing(db, listing, billing_model=tenant.billing_model if tenant else "legacy", enabled_addons=await enabled_addon_slugs(db, listing.tenant_id))` before the commit; the response state comes from `listing.state.value` after retry (no longer hardcoded `"uploading"`; the test above starts with only `ingestion` failed so it will be `uploading`).
- `listings_workflow.py` cancel: add `await cancel_listing_jobs(db, listing.id)` before setting `CANCELLED`; extend `cancellable` to include `ANALYZING`, `AWAITING_REVIEW`, `IN_REVIEW` (the runner cancels in-flight jobs cleanly now).
- `listings_workflow.py` pipeline-status: replace the event-scanning block (lines ~326-370) with `steps = await listing_progress(db, listing.id)`; if `steps` is empty (listing created before this migration) fall back to the old event-derived list. Keep the engagement/features block and the return dict; add `"steps": steps`.
- `api/schemas/listings.py`: `PipelineStepStatus` gains `error: str | None = None` and `attempts: int = 0`.
- `health.py:58-66`: replace the Temporal block with:

```python
    from listingjet.config import settings
    from listingjet.pipeline.runner import WORKER_STATE
    if settings.worker_enabled:
        tick = WORKER_STATE.get("last_tick")
        fresh = tick is not None and (datetime.now(timezone.utc) - tick).total_seconds() < 60
        components["worker"] = "ok" if fresh else "error: no tick in 60s"
    else:
        components["worker"] = "external"
```

Tests: delete the six `patch(... get_temporal_client ...)` lines from `tests/conftest.py` (lines 62-67); in `tests/test_api/test_assets.py` remove the two `@patch("listingjet.api.listings_media.get_temporal_client")` decorators and their `Mock` params; in `tests/test_integration/test_credit_lifecycle.py:308-311` remove the temporal patch context (approval now works without it); in `tests/test_monitoring/test_health.py:22` change `"temporal"` to `"worker"`.

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api tests/test_integration tests/test_monitoring tests/test_pipeline -q -p no:cacheprovider` (timeout 600000). Expected: PASS. Ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/listingjet/api src/listingjet/services/pipeline_start.py tests/conftest.py tests/test_api tests/test_integration tests/test_monitoring
git commit -m "feat(pipeline): API starts, approves, retries, cancels and reports via the job table"
```

---

### Task 9: Remove Temporal

**Files:**
- Delete: `src/listingjet/workflows/` (all), `src/listingjet/activities/` (all), `src/listingjet/temporal_client.py`, `tests/test_workflows/` (all), `tests/test_temporal_client.py`, `docs/TEMPORAL_PIPELINE_GUIDE.md`
- Modify: `src/listingjet/agents/base.py` (remove `_safe_heartbeat`, `heartbeat_during`), `src/listingjet/agents/vision.py`, `src/listingjet/agents/photo_compliance.py`, `src/listingjet/agents/video.py` (remove heartbeat calls), `tests/test_agents/test_base.py` (remove the heartbeat test class), `tests/test_agents/test_chapter.py` and any other test importing from `listingjet.activities` (grep)
- Modify: `pyproject.toml` (drop `temporalio`), `src/listingjet/config/__init__.py` (drop the five `temporal_*` settings), `docker-compose.yml` (drop `temporal`, `temporal-ui`; drop `depends_on: temporal` from api/worker), `render.yaml` (drop `TEMPORAL_*` env keys), `.env.example` and `.env.production.example` (drop `TEMPORAL_*`), `docs/runbooks/render-supabase-cutover.md` (delete the Temporal Cloud section 1c and its step-4 reference), `README.md` and `CLAUDE.md` (replace every "Temporal" mention: pipeline is `src/listingjet/pipeline/`, worker runs in-process, `python -m listingjet.pipeline.worker` standalone)
- Modify: `src/listingjet/api/listings_import.py:45` imports `run_link_import` from `activities.pipeline` — move `LinkImportParams` and `run_link_import` (lines 12-19 and 138-200 of `activities/pipeline.py`) into `src/listingjet/services/link_import_job.py` without the decorator, and update the import.

- [ ] **Step 1: Delete and grep**

```bash
git rm -r src/listingjet/workflows src/listingjet/activities src/listingjet/temporal_client.py tests/test_workflows tests/test_temporal_client.py docs/TEMPORAL_PIPELINE_GUIDE.md
grep -rn "temporal\|Temporal\|listingjet.activities\|listingjet.workflows\|_safe_heartbeat\|heartbeat_during" src tests docs README.md CLAUDE.md pyproject.toml docker-compose.yml render.yaml .env.example .env.production.example --include=* | grep -v "__pycache__"
```

Every hit must be removed or rewritten. `agents/base.py`: delete `_safe_heartbeat`, `heartbeat_during`, and the `asyncio` import if unused. `vision.py`: delete the `_safe_heartbeat(...)` line and import. `photo_compliance.py`: same. `video.py`: replace `async with (heartbeat_during(...), self.session_scope(...) as ...)` with `async with self.session_scope(context) as (session, listing_id, tenant_id):` and re-indent.

- [ ] **Step 2: Reinstall deps and verify the app imports**

Run: `.venv/Scripts/python.exe -m pip install -e ".[dev]" -q` (timeout 600000) after removing `temporalio` from `pyproject.toml`, then `.venv/Scripts/python.exe -m pip uninstall -y temporalio` (timeout 120000) so a stray import fails loudly, then `.venv/Scripts/python.exe -c "import listingjet.main, listingjet.pipeline.worker; print('ok')"`.

- [ ] **Step 3: Full suite and lint**

Run: `.venv/Scripts/python.exe -m pytest --tb=short -q -p no:cacheprovider` (timeout 600000). Expected: 0 failed. `ruff check src tests alembic` clean.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove Temporal (workflows, activities, client, config, compose, docs)"
```

---

### Task 10: Seed script, end-to-end verification, PR

**Files:**
- Create: `scripts/seed_sample_listing.py`
- Modify: `docs/superpowers/plans/2026-09-05-phase2-job-queue.md` (tick boxes only)

- [ ] **Step 1: Seed script**

```python
#!/usr/bin/env python3
"""Create a tenant, admin user, and one listing with 12 generated photos, then
enqueue the pipeline. For local runs with USE_MOCK_PROVIDERS=true.

Usage: .venv/Scripts/python.exe scripts/seed_sample_listing.py
Prints the listing id, the login email/password, and the job list.
"""
import asyncio
import io
import uuid

from PIL import Image, ImageDraw

from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing, ListingState
from listingjet.models.tenant import Tenant
from listingjet.models.user import User, UserRole
from listingjet.pipeline.runner import enqueue_pipeline
from listingjet.services.auth import hash_password
from listingjet.services.storage import get_storage

ROOMS = ["exterior", "exterior", "living_room", "kitchen", "kitchen", "dining_room",
         "bedroom", "bedroom", "bedroom", "bathroom", "bathroom", "backyard"]


def _photo(label: str, i: int) -> bytes:
    img = Image.new("RGB", (1600, 1067), (40 + i * 15, 90, 160 - i * 10))
    ImageDraw.Draw(img).text((40, 40), f"{label} #{i}", fill="white")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue()


async def main() -> None:
    storage = get_storage()
    async with AsyncSessionLocal() as db:
        tenant = Tenant(id=uuid.uuid4(), name="Seed Realty", plan="starter", billing_model="legacy")
        user = User(id=uuid.uuid4(), tenant_id=tenant.id, email=f"seed-{uuid.uuid4().hex[:6]}@example.com",
                    password_hash=hash_password("SeedPass1!"), role=UserRole.ADMIN, name="Seed Admin")
        listing = Listing(id=uuid.uuid4(), tenant_id=tenant.id,
                          address={"street": "123 Sample St", "city": "Austin", "state": "TX", "zip": "78701"},
                          metadata_={"beds": 3, "baths": 2, "sqft": 1850, "price": 525000},
                          state=ListingState.UPLOADING)
        db.add_all([tenant, user, listing])
        await db.flush()
        for i, room in enumerate(ROOMS):
            key = f"listings/{listing.id}/uploads/{uuid.uuid4()}/{room}_{i}.jpg"
            storage.upload_bytes(_photo(room, i), key=key, content_type="image/jpeg")
            db.add(Asset(tenant_id=tenant.id, listing_id=listing.id, file_path=key,
                         file_hash=f"seed{i:02d}", state="uploaded"))
        jobs = await enqueue_pipeline(db, listing, billing_model="legacy", enabled_addons=[])
        await db.commit()
    print(f"listing_id={listing.id}\nlogin={user.email} / SeedPass1!\njobs={[j.step for j in jobs]}")


if __name__ == "__main__":
    asyncio.run(main())
```

Check the `Tenant`/`User` constructor fields against `models/tenant.py` and `models/user.py` and the storage factory name (`get_storage` in `services/storage.py`); with `USE_MOCK_PROVIDERS=true` and no S3 credentials, `storage.upload_bytes` needs a mock — if `StorageService` has no mock mode, set `S3_ENDPOINT_URL` to a moto server or wrap the upload in `try/except` and print a warning; the mock ingestion agent does not read the bytes.

- [ ] **Step 2: Run the pipeline locally end to end with mock providers**

In one terminal (Bash, `run_in_background: true`, timeout 600000): `USE_MOCK_PROVIDERS=true .venv/Scripts/python.exe -m listingjet.pipeline.worker > .superpowers/worker.log 2>&1`.
Then: `.venv/Scripts/python.exe scripts/seed_sample_listing.py` (timeout 120000). Poll with `C:/Users/label/tools/pgsql/bin/psql.exe -h localhost -p 5432 -U listingjet -d listingjet -c "select step,status,attempts,left(error,60) from pipeline_jobs where listing_id='<id>' order by created_at"` (env `PGPASSWORD=password`) until `await_review` is the only non-terminal row and `listings.state = 'awaiting_review'`. Then `update pipeline_jobs set status='done' where listing_id='<id>' and step='await_review'` (or call `/approve` through the API) and watch it reach `distribution = done` and `listings.state = 'delivered'`. Record the timings in the PR body.

- [ ] **Step 3: Crash and failure drills**

- Kill the worker (`taskkill` on its PID) while a step is `running`; set that row's `locked_at` back 1 hour with psql; restart the worker; confirm the row is reclaimed and finishes.
- Seed again, then `update pipeline_jobs set payload = payload || '{"force_error": true}'` is not wired, so instead patch: temporarily set `USE_MOCK_PROVIDERS=false` with no API keys so `ingestion` succeeds but `vision_tier1` raises; confirm `listings.state='failed'`, the `pipeline.failed` event exists, downstream rows are `cancelled`; call `/retry` through the API and confirm rows requeue. Restore env.

- [ ] **Step 4: Full suite, lint, PR**

Run: `.venv/Scripts/python.exe -m pytest --tb=short -q -p no:cacheprovider` (timeout 600000) and `ruff check src tests alembic`.

```bash
git add scripts/seed_sample_listing.py
git commit -m "chore: sample listing seed script for local pipeline runs"
git push -u origin feat/job-queue
gh pr create --base fix/security-week1 --title "feat: Postgres job queue replaces Temporal (phase 2)" --body-file <write the body from the summary below>
```

If PR #306 has merged, use `--base main` after `git rebase main`. PR body: what replaced what, the two latent bugs fixed (social_event import, demo cleanup storage), the dependency change that makes `distribution` wait for social steps, the end-to-end run timings, and the drills. End with the two attribution lines. Do not merge.

## Self-review notes (done while writing)

- Spec coverage: schema ✓ (T1), definition ✓ (T2), runner claim/run/failure/timeout/reclaim/concurrency ✓ (T4, T5, T7), `to_thread` for CPU work — deferred to Phase 6 where the video code is rewritten (called out here so it is not lost), approve/retry/cancel/status ✓ (T6, T8), heartbeat removal ✓ (T9), split-transaction agents — deferred to Phase 4-6 rewrites (the runner already opens no transaction around the step call), removal list ✓ (T9), demo/baseline periodic ✓ (T7), storage=None bug ✓ (T7), tests ✓.
- Type consistency: `enqueue_pipeline(session, listing, *, billing_model, enabled_addons, steps)`, `claim_next(session, worker_id, *, steps)`, `run_job(session_factory, job_id, *, steps, functions)`, `complete_review(session, listing_id)`, `retry_listing(session, listing, *, steps, billing_model, enabled_addons)`, `cancel_listing_jobs(session, listing_id)`, `listing_progress(session, listing_id, *, steps)` are used with those exact shapes in T4–T8.
