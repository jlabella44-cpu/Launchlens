# Session 22: Learning Feedback Loop — Wire Agent, Track Overrides, Fix Weights

## Context
The learning infrastructure exists (LearningWeight with alpha/beta, PerformanceEvent, WeightManager with Thompson Sampling) but the loop is disconnected:
- LearningAgent exists but is NOT in the pipeline workflow
- Packaging agent hardcodes `room_weight = 1.0` instead of loading weights
- No API for reviewers to reorder photos (which would emit override events)
- PerformanceEvent table is unused

## Task 1: Wire LearningAgent into Pipeline
**File:** `src/launchlens/workflows/listing_pipeline.py`

Add after the distribution step (final step of Phase 2):
```python
# Learn from human overrides for this listing
await workflow.execute_activity(
    run_learning, ctx,
    start_to_close_timeout=_DEFAULT_TIMEOUT,
    retry_policy=_DEFAULT_RETRY,
)
```

Import `run_learning` from `activities/pipeline.py`. If it doesn't exist there, add:
```python
@activity.defn
async def run_learning(context: AgentContext) -> dict:
    from launchlens.agents.learning import LearningAgent
    return await LearningAgent().execute(context)
```

Also add it to `ALL_ACTIVITIES` list.

## Task 2: Photo Reorder Endpoint
**File:** `src/launchlens/api/listings.py`

Add `POST /listings/{id}/package/reorder` for reviewers to swap photo positions:
```python
@router.post("/{listing_id}/package/reorder")
async def reorder_package(listing_id, body, current_user, db):
    # body: {"swaps": [{"from_position": 0, "to_position": 3}, ...]}
    # Update PackageSelection positions
    # Emit override events:
    #   "package.override.swap_to" for the photo moved up
    #   "package.override.swap_from" for the photo moved down
    # Include room_label in event payload (learning agent needs this)
```

## Task 3: Fix Packaging Agent Weight Loading
**File:** `src/launchlens/agents/packaging.py`

If line 54 still has `room_weight: 1.0  # TODO`, replace with actual LearningWeight query. Load weights for the tenant, use alpha/beta for Thompson Sampling in `WeightManager.score()`.

## Task 4: Performance Event Ingestion
The `PerformanceEvent` model exists but nothing writes to it. Add tracking:

**File:** `src/launchlens/agents/distribution.py`

After marking DELIVERED, record a performance event:
```python
from launchlens.models.performance_event import PerformanceEvent
pe = PerformanceEvent(
    tenant_id=tenant_id, listing_id=listing_id,
    signal_type="listing_delivered", value=1.0, source="pipeline",
)
session.add(pe)
```

**File:** `src/launchlens/api/listings.py`

After export download, record:
```python
pe = PerformanceEvent(
    tenant_id=..., listing_id=...,
    signal_type="export_downloaded", value=1.0, source="user",
)
```

## Task 5: Weight Decay
**File:** `src/launchlens/services/weight_manager.py`

Add a method for gradual weight decay:
```python
def apply_decay(self, alpha: float, beta_param: float, days_since_update: int) -> tuple[float, float]:
    """Regress stale weights toward (1.0, 1.0) after 90 days."""
    if days_since_update < 90:
        return alpha, beta_param
    decay = min(0.1 * ((days_since_update - 90) / 30), 0.5)  # max 50% decay
    alpha = alpha * (1 - decay) + 1.0 * decay
    beta_param = beta_param * (1 - decay) + 1.0 * decay
    return alpha, beta_param
```

Call in packaging agent before scoring if weight's `updated_at` is old.

## Verification
- Complete listing → learning agent runs → LearningWeight rows updated
- Reviewer reorders photos → override events emitted with room_label
- Next listing: packaging agent uses actual weights (verify with logging)
- `WeightManager.score()` uses alpha/beta from DB, not 1.0
- PerformanceEvent table has rows after listing delivery + export download
