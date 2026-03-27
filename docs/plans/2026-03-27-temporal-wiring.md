# Temporal Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the Temporal workflow to execute all pipeline agents as activities, wait for the human review signal between packaging and content, and trigger the pipeline from the asset registration API endpoint.

**Architecture:** Each agent gets a thin `@activity.defn` wrapper function in `activities/pipeline.py`. The `ListingPipeline` workflow calls these activities in sequence: Ingestion → Vision Tier 1 → Vision Tier 2 → Coverage → Packaging → [wait for `human_review_completed` signal] → Content → Brand → Distribution. A shared `TemporalClient` singleton starts workflows. The `register_assets` endpoint starts the pipeline after transitioning to UPLOADING.

**Tech Stack:** temporalio>=1.7 (already installed), FastAPI, SQLAlchemy 2.0 async

---

## File Structure

```
src/launchlens/
  activities/
    __init__.py              CREATE  — empty package
    pipeline.py              CREATE  — @activity.defn wrappers for each agent step
  workflows/
    listing_pipeline.py      MODIFY  — wire run() to execute activities in sequence
    worker.py                CREATE  — Temporal worker process
  temporal_client.py         CREATE  — shared TemporalClient for starting workflows
  api/listings.py            MODIFY  — trigger pipeline from register_assets

tests/test_workflows/
  test_activities.py         CREATE  — activity function tests
  test_listing_pipeline.py   MODIFY  — workflow wiring tests
```

---

## Key Patterns

### Activity input
All activities share the same input — `listing_id` and `tenant_id` as strings. We reuse the existing `AgentContext` dataclass.

### Activity wrapper pattern
```python
@activity.defn
async def run_ingestion(context: AgentContext) -> dict:
    agent = IngestionAgent()
    return await agent.execute(context)
```
Each wrapper instantiates the agent with production defaults (no args) and calls `execute()`. In tests, agents are tested directly — activities are thin wrappers.

### VisionAgent has two tiers
`VisionAgent.run_tier1(ctx)` and `VisionAgent.run_tier2(ctx)` are separate methods, not `execute()`. They get their own activity wrappers.

### Workflow timeout + retry
Activities get `start_to_close_timeout=timedelta(minutes=10)` and `retry_policy=RetryPolicy(maximum_attempts=3)`. Vision Tier 2 (GPT-4V calls) gets `timedelta(minutes=20)`.

### Temporal client lifecycle
The `TemporalClient` connects lazily on first use. In tests, it's mocked. The `register_assets` endpoint calls `await temporal_client.start_pipeline(listing_id, tenant_id)`.

---

## Tasks

---

### Task 1: Activity definitions

**Files:**
- Create: `src/launchlens/activities/__init__.py`
- Create: `src/launchlens/activities/pipeline.py`
- Create: `tests/test_workflows/test_activities.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_workflows/test_activities.py`:

```python
# tests/test_workflows/test_activities.py
import pytest
from temporalio import activity


def test_all_activities_are_decorated():
    """All pipeline activity functions must have @activity.defn."""
    from launchlens.activities.pipeline import (
        run_ingestion,
        run_vision_tier1,
        run_vision_tier2,
        run_coverage,
        run_packaging,
        run_content,
        run_brand,
        run_distribution,
    )
    for fn in [
        run_ingestion, run_vision_tier1, run_vision_tier2,
        run_coverage, run_packaging, run_content, run_brand, run_distribution,
    ]:
        assert hasattr(fn, "__temporal_activity_definition"), f"{fn.__name__} missing @activity.defn"


def test_activity_names():
    """Activity names should match expected convention."""
    from launchlens.activities.pipeline import (
        run_ingestion, run_vision_tier1, run_vision_tier2,
        run_coverage, run_packaging, run_content, run_brand, run_distribution,
    )
    expected = [
        "run_ingestion", "run_vision_tier1", "run_vision_tier2",
        "run_coverage", "run_packaging", "run_content", "run_brand", "run_distribution",
    ]
    fns = [run_ingestion, run_vision_tier1, run_vision_tier2,
           run_coverage, run_packaging, run_content, run_brand, run_distribution]
    for fn, name in zip(fns, expected):
        assert fn.__temporal_activity_definition.name == name
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_workflows/test_activities.py -v 2>&1 | tail -10
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement activity definitions**

Create `src/launchlens/activities/__init__.py` (empty).

Create `src/launchlens/activities/pipeline.py`:

```python
from temporalio import activity
from launchlens.agents.base import AgentContext


@activity.defn
async def run_ingestion(context: AgentContext) -> dict:
    from launchlens.agents.ingestion import IngestionAgent
    return await IngestionAgent().execute(context)


@activity.defn
async def run_vision_tier1(context: AgentContext) -> int:
    from launchlens.agents.vision import VisionAgent
    return await VisionAgent().run_tier1(context)


@activity.defn
async def run_vision_tier2(context: AgentContext) -> int:
    from launchlens.agents.vision import VisionAgent
    return await VisionAgent().run_tier2(context)


@activity.defn
async def run_coverage(context: AgentContext) -> dict:
    from launchlens.agents.coverage import CoverageAgent
    return await CoverageAgent().execute(context)


@activity.defn
async def run_packaging(context: AgentContext) -> dict:
    from launchlens.agents.packaging import PackagingAgent
    return await PackagingAgent().execute(context)


@activity.defn
async def run_content(context: AgentContext) -> dict:
    from launchlens.agents.content import ContentAgent
    return await ContentAgent().execute(context)


@activity.defn
async def run_brand(context: AgentContext) -> dict:
    from launchlens.agents.brand import BrandAgent
    return await BrandAgent().execute(context)


@activity.defn
async def run_distribution(context: AgentContext) -> dict:
    from launchlens.agents.distribution import DistributionAgent
    return await DistributionAgent().execute(context)


# Collect all activities for worker registration
ALL_ACTIVITIES = [
    run_ingestion, run_vision_tier1, run_vision_tier2,
    run_coverage, run_packaging, run_content, run_brand, run_distribution,
]
```

Note: Imports are inside the function bodies to avoid circular imports and to keep the activity module lightweight.

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_workflows/test_activities.py -v 2>&1 | tail -10
```
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/activities/__init__.py src/launchlens/activities/pipeline.py tests/test_workflows/test_activities.py && git commit -m "feat: add Temporal activity definitions for pipeline agents"
```

---

### Task 2: Workflow implementation

**Files:**
- Modify: `src/launchlens/workflows/listing_pipeline.py`
- Modify: `tests/test_workflows/test_listing_pipeline.py`

- [ ] **Step 1: Write failing tests**

Replace `tests/test_workflows/test_listing_pipeline.py` entirely:

```python
# tests/test_workflows/test_listing_pipeline.py
import pytest
from unittest.mock import patch, AsyncMock
from launchlens.workflows.listing_pipeline import ListingPipeline, ListingPipelineInput


def test_pipeline_input_dataclass():
    inp = ListingPipelineInput(listing_id="abc-123", tenant_id="tenant-xyz")
    assert inp.listing_id == "abc-123"
    assert inp.tenant_id == "tenant-xyz"


def test_pipeline_workflow_has_required_signals():
    assert hasattr(ListingPipeline, "shadow_review_approved")
    assert hasattr(ListingPipeline, "human_review_completed")


def test_pipeline_init_sets_flags():
    pipeline = ListingPipeline()
    assert pipeline._shadow_approved is False
    assert pipeline._review_completed is False


@pytest.mark.asyncio
async def test_shadow_review_signal_sets_flag():
    pipeline = ListingPipeline()
    await pipeline.shadow_review_approved()
    assert pipeline._shadow_approved is True


@pytest.mark.asyncio
async def test_human_review_signal_sets_flag():
    pipeline = ListingPipeline()
    await pipeline.human_review_completed()
    assert pipeline._review_completed is True


def test_pipeline_imports_activities():
    """Workflow module must reference all pipeline activities."""
    from launchlens.workflows import listing_pipeline
    source = open(listing_pipeline.__file__).read()
    expected_activities = [
        "run_ingestion", "run_vision_tier1", "run_vision_tier2",
        "run_coverage", "run_packaging", "run_content", "run_brand", "run_distribution",
    ]
    for act in expected_activities:
        assert act in source, f"Workflow does not reference activity: {act}"


def test_pipeline_has_retry_policy():
    """Workflow source should contain RetryPolicy configuration."""
    from launchlens.workflows import listing_pipeline
    source = open(listing_pipeline.__file__).read()
    assert "RetryPolicy" in source
    assert "start_to_close_timeout" in source
```

- [ ] **Step 2: Run tests to verify new ones fail**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_workflows/test_listing_pipeline.py -v 2>&1 | tail -15
```
Expected: `test_pipeline_imports_activities` and `test_pipeline_has_retry_policy` FAIL

- [ ] **Step 3: Implement workflow wiring**

Replace `src/launchlens/workflows/listing_pipeline.py` entirely:

```python
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from launchlens.agents.base import AgentContext
    from launchlens.activities.pipeline import (
        run_ingestion,
        run_vision_tier1,
        run_vision_tier2,
        run_coverage,
        run_packaging,
        run_content,
        run_brand,
        run_distribution,
    )


@dataclass
class ListingPipelineInput:
    listing_id: str
    tenant_id: str


_DEFAULT_RETRY = RetryPolicy(maximum_attempts=3)
_DEFAULT_TIMEOUT = timedelta(minutes=10)
_VISION_TIER2_TIMEOUT = timedelta(minutes=20)


@workflow.defn
class ListingPipeline:
    """
    LaunchLens listing processing pipeline.

    ┌──────────────────────────────────────────────────────────────┐
    │  Ingestion → Vision T1 → Vision T2 → Coverage → Packaging  │
    │                                                              │
    │              [wait for human_review_completed]               │
    │                                                              │
    │              Content → Brand → Distribution                  │
    └──────────────────────────────────────────────────────────────┘
    """

    def __init__(self) -> None:
        self._shadow_approved = False
        self._review_completed = False

    @workflow.run
    async def run(self, input: ListingPipelineInput) -> str:
        ctx = AgentContext(listing_id=input.listing_id, tenant_id=input.tenant_id)

        # Phase 1: Analysis pipeline
        await workflow.execute_activity(
            run_ingestion, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        await workflow.execute_activity(
            run_vision_tier1, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        await workflow.execute_activity(
            run_vision_tier2, ctx,
            start_to_close_timeout=_VISION_TIER2_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        await workflow.execute_activity(
            run_coverage, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        await workflow.execute_activity(
            run_packaging, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )

        # Wait for human review (listing is now AWAITING_REVIEW)
        await workflow.wait_condition(lambda: self._review_completed)

        # Phase 2: Post-approval pipeline
        await workflow.execute_activity(
            run_content, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        await workflow.execute_activity(
            run_brand, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        await workflow.execute_activity(
            run_distribution, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )

        return f"pipeline_complete:{input.listing_id}"

    @workflow.signal
    async def shadow_review_approved(self) -> None:
        self._shadow_approved = True

    @workflow.signal
    async def human_review_completed(self) -> None:
        self._review_completed = True
```

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_workflows/test_listing_pipeline.py -v 2>&1 | tail -15
```
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/workflows/listing_pipeline.py tests/test_workflows/test_listing_pipeline.py && git commit -m "feat: wire ListingPipeline to execute all agent activities in sequence"
```

---

### Task 3: Worker + client + API trigger + tag

**Files:**
- Create: `src/launchlens/workflows/worker.py`
- Create: `src/launchlens/temporal_client.py`
- Modify: `src/launchlens/api/listings.py`
- Create: `tests/test_workflows/test_worker.py`
- Modify: `tests/test_api/test_assets.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_workflows/test_worker.py`:

```python
# tests/test_workflows/test_worker.py
import pytest


def test_worker_module_imports():
    """Worker module must be importable and expose create_worker."""
    from launchlens.workflows.worker import create_worker
    assert callable(create_worker)


def test_worker_registers_all_activities():
    """Worker source must register ALL_ACTIVITIES."""
    from launchlens.workflows import worker
    source = open(worker.__file__).read()
    assert "ALL_ACTIVITIES" in source
    assert "ListingPipeline" in source
```

Append to `tests/test_api/test_assets.py`:

```python
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
@patch("launchlens.api.listings.get_temporal_client")
async def test_register_assets_triggers_pipeline(mock_get_client, async_client: AsyncClient):
    """Registering assets should start the Temporal pipeline."""
    mock_client = AsyncMock()
    mock_get_client.return_value = mock_client

    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Pipeline St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    resp = await async_client.post(f"/listings/{listing_id}/assets", json={
        "assets": [{"file_path": "s3://bucket/photo.jpg", "file_hash": "abc"}]
    }, headers=_auth(token))
    assert resp.status_code == 201
    mock_client.start_pipeline.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_workflows/test_worker.py tests/test_api/test_assets.py::test_register_assets_triggers_pipeline -v 2>&1 | tail -15
```
Expected: FAIL — module not found

- [ ] **Step 3: Create Temporal client**

Create `src/launchlens/temporal_client.py`:

```python
import uuid
from temporalio.client import Client
from launchlens.config import settings
from launchlens.workflows.listing_pipeline import ListingPipeline, ListingPipelineInput


class TemporalClient:
    def __init__(self):
        self._client: Client | None = None

    async def _connect(self) -> Client:
        if self._client is None:
            self._client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)
        return self._client

    async def start_pipeline(self, listing_id: str, tenant_id: str) -> str:
        client = await self._connect()
        workflow_id = f"listing-pipeline-{listing_id}"
        handle = await client.start_workflow(
            ListingPipeline.run,
            ListingPipelineInput(listing_id=listing_id, tenant_id=tenant_id),
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
        return handle.id

    async def signal_review_completed(self, listing_id: str) -> None:
        client = await self._connect()
        workflow_id = f"listing-pipeline-{listing_id}"
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal(ListingPipeline.human_review_completed)


_temporal_client: TemporalClient | None = None


def get_temporal_client() -> TemporalClient:
    global _temporal_client
    if _temporal_client is None:
        _temporal_client = TemporalClient()
    return _temporal_client
```

- [ ] **Step 4: Create worker**

Create `src/launchlens/workflows/worker.py`:

```python
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from launchlens.config import settings
from launchlens.workflows.listing_pipeline import ListingPipeline
from launchlens.activities.pipeline import ALL_ACTIVITIES


async def create_worker() -> Worker:
    client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)
    return Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[ListingPipeline],
        activities=ALL_ACTIVITIES,
    )


async def main():
    worker = await create_worker()
    print(f"Worker started on queue: {settings.temporal_task_queue}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 5: Update register_assets to trigger pipeline**

Read `src/launchlens/api/listings.py` first. Modify the `register_assets` function to start the pipeline after transitioning to UPLOADING:

Add imports at top:
```python
import logging
from launchlens.temporal_client import get_temporal_client

logger = logging.getLogger(__name__)
```

After the `await db.commit()` in `register_assets`, add:
```python
    # Trigger the pipeline if listing just entered UPLOADING
    if listing.state == ListingState.UPLOADING:
        try:
            client = get_temporal_client()
            await client.start_pipeline(
                listing_id=str(listing.id),
                tenant_id=str(current_user.tenant_id),
            )
        except Exception:
            logger.exception("Pipeline trigger failed for listing %s", listing.id)
```

Also update the `approve_listing` function to signal the workflow. After setting state to APPROVED and committing:
```python
    # Signal the waiting workflow to continue post-approval pipeline
    try:
        client = get_temporal_client()
        await client.signal_review_completed(listing_id=str(listing.id))
    except Exception:
        logger.exception("Review signal failed for listing %s", listing.id)
```

- [ ] **Step 6: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_workflows/test_worker.py tests/test_api/test_assets.py -v 2>&1 | tail -20
```

- [ ] **Step 7: Run full suite**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest --tb=short -q 2>&1 | tail -15
```

- [ ] **Step 8: Commit and tag**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/temporal_client.py src/launchlens/workflows/worker.py src/launchlens/api/listings.py tests/test_workflows/test_worker.py tests/test_api/test_assets.py && git commit -m "feat: add Temporal worker, client, and pipeline trigger from API" && git tag v0.7.0-temporal-wiring && echo "Tagged v0.7.0-temporal-wiring"
```

---

## NOT in scope

- Temporal server deployment / Docker Compose setup — dev uses local Temporal CLI
- Temporal UI configuration — use default Temporal web UI
- Workflow cancellation / compensation — deferred
- Shadow review signal flow — implemented in workflow but not triggered by API (deferred)
- LearningAgent as a separate Temporal workflow — deferred (triggered by events, not pipeline)
- Workflow versioning / migration strategy — deferred to production hardening plan
- Temporal cron/scheduled workflows — not needed for on-demand pipeline

## What already exists

- `ListingPipeline` workflow class with signal handlers (`shadow_review_approved`, `human_review_completed`)
- `ListingPipelineInput` dataclass (`listing_id`, `tenant_id`)
- All 8 agents fully implemented with `execute()` methods (+ VisionAgent `run_tier1`, `run_tier2`)
- `AgentContext` dataclass matching `ListingPipelineInput` shape
- Config: `temporal_host`, `temporal_namespace`, `temporal_task_queue`
- `temporalio>=1.7` in pyproject.toml
- `register_assets` endpoint transitions listing to UPLOADING
- `approve_listing` endpoint transitions listing to APPROVED
- Pipeline tests in `tests/test_workflows/test_listing_pipeline.py`
