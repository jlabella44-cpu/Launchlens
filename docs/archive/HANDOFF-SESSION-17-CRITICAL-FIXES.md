# Session 17: CRITICAL — Worker Activities, Migration Chain, CORS

## Priority: P0 — These bugs block production deployment.

## Bug 1: Temporal Worker Registers Zero Activities
**File:** `src/launchlens/worker.py` line 19

`activities=[]` — the worker has no activities registered. The pipeline workflow calls `run_ingestion`, `run_vision_tier1`, etc. but the worker can't execute them. The `ALL_ACTIVITIES` list exists in `src/launchlens/activities/pipeline.py` lines 97-101 but is never imported.

**Fix:**
```python
from launchlens.activities.pipeline import ALL_ACTIVITIES
# Then in Worker():
activities=ALL_ACTIVITIES
```

## Bug 2: Alembic Migration Chain Broken
Four migration files all have `revision = "010"` and `down_revision = "009"`:
- `010_credit_accounts_billing_model.py`
- `010_credit_system.py`
- `010_credit_transactions.py`
- `010_notification_preferences.py`

`alembic upgrade head` will fail with "multiple heads" error.

**Fix:** Merge all four into a single `010_unified_credit_system.py` that creates all tables in one migration. Or renumber to 010/011/012/013 with proper `down_revision` chain. Verify with `alembic heads` — must show exactly 1 head.

## Bug 3: No CORS Middleware
**File:** `src/launchlens/main.py`

FastAPI has NO CORSMiddleware. Browser requests from the frontend will fail.

**Fix:** Add to `create_app()`:
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"] if settings.app_env == "development" else [settings.cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Add `cors_origins: str = "http://localhost:3000"` to `src/launchlens/config.py`.

## Verification
- `alembic upgrade head` succeeds, `alembic heads` shows 1 head
- Worker logs show all registered activities on startup
- Frontend can make API requests without CORS errors
- `pytest tests/ -x` — no regressions
