# Session 19: Test Coverage Expansion — Missing Agents, SSE, Middleware, Providers

## Context
~40 source modules lack test coverage. Critical untested code: chapter agent, learning agent, watermark agent, SSE endpoint, all middleware, most providers. The packaging agent also has a hardcoded `room_weight = 1.0` that should use Thompson Sampling weights.

## Task 1: Missing Agent Tests

**`tests/test_agents/test_chapter.py`:**
- Test ChapterAgent with mock vision provider returning chapter JSON
- Test skipping when no video exists
- Test handling of invalid JSON from provider

**`tests/test_agents/test_learning.py`:**
- Test LearningAgent processes override events
- Test weight update creates/updates LearningWeight rows
- Test alpha/beta Thompson Sampling params update correctly

**`tests/test_agents/test_watermark.py`:**
- Test WatermarkAgent applies text watermark to image bytes
- Test brand kit text extraction (brokerage + agent name)
- Test graceful failure when image bytes are invalid

Use `make_session_factory(db_session)` pattern from `tests/test_agents/conftest.py`.

## Task 2: Fix Packaging Agent Weight Loading
**File:** `src/launchlens/agents/packaging.py` line 54

Check if this is still `room_weight: 1.0  # TODO`. If so, fix:
```python
from launchlens.models.learning_weight import LearningWeight

# Inside execute(), after loading VisionResults:
lw_result = await session.execute(
    select(LearningWeight).where(LearningWeight.tenant_id == uuid.UUID(context.tenant_id))
)
weight_map = {lw.room_label: lw for lw in lw_result.scalars().all()}

# In scoring loop:
lw = weight_map.get(vr.room_label)
features = {
    "quality_score": vr.quality_score or 50,
    "commercial_score": vr.commercial_score or 50,
    "hero_candidate": vr.hero_candidate or False,
    "alpha": lw.alpha if lw else 1.0,
    "beta_param": lw.beta_param if lw else 1.0,
}
```

## Task 3: SSE Endpoint Tests
**New file:** `tests/test_api/test_sse.py`

- Test `GET /listings/{id}/events` returns `text/event-stream`
- Test requires authentication (401 without token)
- Test 404 for non-existent listing

## Task 4: Middleware Tests
**New file:** `tests/test_middleware/test_security_headers.py`

- Test HSTS header present
- Test X-Content-Type-Options: nosniff
- Test CSP header present

**Extend:** `tests/test_middleware/test_rate_limit.py` if it doesn't cover 429 responses.

## Task 5: Provider Tests
**`tests/test_providers/test_canva.py`** — mock httpx, test Claude design JSON → Canva render flow
**`tests/test_providers/test_kling.py`** — mock httpx, test clip generation + status polling
**`tests/test_providers/test_claude.py`** — mock anthropic client, test completion

## Task 6: Coverage Config
Ensure `pyproject.toml` has:
```toml
[tool.coverage.run]
source = ["src/launchlens"]
omit = ["*/test*", "*/migrations/*"]

[tool.coverage.report]
fail_under = 70
show_missing = true
```

## Verification
- `pytest tests/ -v` — all pass
- `pytest tests/ --cov --cov-report=term-missing` — coverage > 70%
- No hardcoded `room_weight = 1.0` in packaging agent
