# Phase 4: Claude Provider Layer and Photo Analysis — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Google Vision plus two GPT-4o passes with one structured Claude call per photo, move floorplan reading to Sonnet 5 with real multi-image input, stage only empty rooms, record real token usage, and collapse the provider layer to three clients.

**Architecture:** A `ClaudeClient` (anthropic SDK 1.x, `messages.parse` with Pydantic schemas) is the only text/vision provider; an `OpenAIImagesClient` (raw httpx, as today) is the only image-generation provider; `MockClaudeClient` and the existing image mocks serve tests. A new `photo_analysis` pipeline step writes one `VisionResult` row per asset (tier 1, extended columns from migration 055) that every downstream consumer already reads. Compliance is persisted on that row and served from it; the separate compliance step, both vision tiers, and the tier-2 concept are deleted.

**Tech Stack:** Python 3.12, `anthropic` 1.4.0 (installed), Pydantic 2, httpx, SQLAlchemy 2 async, Alembic, pytest + pytest-httpx.

**Spec:** `docs/superpowers/specs/2026-09-05-free-tier-rework-design.md` (section "Phase 4: provider layer and photo analysis").

## Global Constraints

- Branch `feat/claude-providers`, created off `chore/delete-and-flag` (PR #308, unmerged; stacked on #307 → #306). PR targets `chore/delete-and-flag`; never push to `main`; do not merge.
- Tooling: `.venv/Scripts/python.exe -m pytest <paths> -q --tb=short -p no:cacheprovider` (full suite ≈ 440 s, `timeout: 600000`); `.venv/Scripts/ruff.exe check src tests alembic`; `.venv/Scripts/alembic.exe <cmd>`. Postgres dev (5432, at 054) and test (5433) running; `.env` exists with `USE_MOCK_PROVIDERS=true`. Never run two pytest processes at once (shared test DB; `tests/test_pipeline/conftest.py` wipes `pipeline_jobs`). Never `npm run build`.
- Alembic head is `054_drop_cut_tables`; new migration `055_vision_result_analysis` with `down_revision = "054_drop_cut_tables"`.
- Model IDs come from settings: `claude_fast_model = "claude-haiku-4-5"` (per-photo classification), `claude_quality_model = "claude-sonnet-5"` (copy, floorplan). Never append date suffixes. Sonnet 5 / Haiku 4.5 reject `temperature`/`top_p` — the client must never send them. Thinking is left at the model default (omit the parameter). `max_tokens` default 4096; floorplan 8000.
- Structured outputs via `client.messages.parse(..., output_format=<PydanticModel>)` → `response.parsed_output`; `None` (refusal/parse failure) raises `ProviderOutputError`. Images via content blocks `{"type": "image", "source": {"type": "url", "url": <presigned R2 URL>}}` placed before the text block.
- Token usage is recorded from `response.usage.input_tokens` / `output_tokens` through `services.metrics.record_token_usage(model_id, input, output, agent_name)`; rates live in `config/ai_rates.py` keyed by model id.
- Agents are NOT split into load→call→save here beyond `photo_analysis` (new code) — that refactor rides with each agent's rewrite.
- Commit messages end with:
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01FN81v1ehP7Snv3UsWaRf9D
  ```

## Findings that shape this plan (verified)

- `anthropic` 1.4.0 is installed; the `openai` SDK is not — the image providers use raw httpx and stay that way (ruling: no new dependency).
- `ClaudeProvider.complete()` passes `temperature`, which current models reject — the reason the Phase 2 failure drill's `content` step failed deterministically. The shim in Task 1 drops it; tone is expressed through the system prompt only.
- Every downstream consumer reads `VisionResult` rows with `tier == 1` (content, coverage, floorplan, mls_export, packaging, video, virtual_staging, health_score, performance_intelligence, listings_media). Writing the new analysis as tier 1 keeps them all working; `packaging` orders by `tier.desc()` which is harmless with a single tier.
- `photo_compliance` results are not persisted today; `api/image_edit.py` re-runs the agent to get them, and `api/listings_workflow.py` has a `/compliance` endpoint that does the same. Both will read the persisted `compliance` JSON instead.
- `services/metrics.py` rate cards are keyed by provider label (`"claude"`, `"openai_gpt4v"`); Task 2 re-keys by model id.
- `services/help_agent.py:21` pins `claude-sonnet-4-6` and uses its own client; it is flag-off code — Task 1 only points it at `settings.claude_quality_model` and the shared client, no behaviour change.

## File structure

| File | Responsibility |
|---|---|
| `src/listingjet/providers/claude.py` | `ClaudeClient` (`complete_text`, `complete_json`, `analyze_images`), `ProviderOutputError`; `ClaudeProvider` shim |
| `src/listingjet/providers/mock.py` | `MockClaudeClient` (+ existing image/template mocks) |
| `src/listingjet/providers/openai_images.py` | `OpenAIImagesClient` merging `_openai_edits`, `openai_staging`, `openai_dollhouse`, `openai_image_edit` |
| `src/listingjet/providers/factory.py` | `get_claude()`, `get_openai_images()`, `get_template_provider()`, `get_virtual_staging_provider()`, `get_image_edit_provider()` |
| `src/listingjet/config/ai_rates.py` | per-model token rates + per-call image rates |
| `src/listingjet/agents/photo_analysis.py` | `PhotoAnalysis` schema, `PhotoAnalysisAgent` |
| `src/listingjet/services/compliance.py` | `compliance_report(session, listing_id) -> dict` from persisted rows |
| `alembic/versions/055_vision_result_analysis.py` | new columns |

---

### Task 1: `ClaudeClient` and the shim

**Files:**
- Modify: `src/listingjet/providers/claude.py` (rewrite), `src/listingjet/config/__init__.py` (add `claude_fast_model`, `claude_quality_model`), `src/listingjet/services/help_agent.py:21` (model constant → settings), `src/listingjet/providers/factory.py` (add `get_claude()`), `src/listingjet/providers/mock.py` (add `MockClaudeClient`), `src/listingjet/providers/__init__.py` (export)
- Test: `tests/test_providers/test_claude.py` (rewrite)

**Interfaces:**
- Produces:
  ```python
  class ProviderOutputError(RuntimeError): ...
  class ClaudeClient:
      def __init__(self, api_key: str | None = None): ...
      async def complete_text(self, prompt: str, *, system: str | None = None, model: str | None = None,
                              max_tokens: int = 4096, agent: str | None = None) -> str
      async def complete_json(self, prompt: str, schema: type[BaseModel], *, system: str | None = None,
                              model: str | None = None, max_tokens: int = 4096, agent: str | None = None) -> BaseModel
      async def analyze_images(self, image_urls: list[str], prompt: str, schema: type[BaseModel], *,
                               system: str | None = None, model: str | None = None, max_tokens: int = 4096,
                               agent: str | None = None) -> BaseModel
  class MockClaudeClient:  # same three methods; complete_json/analyze_images build `schema.model_validate(schema_defaults(schema, seed))`
  def get_claude() -> ClaudeClient | MockClaudeClient   # factory
  class ClaudeProvider(LLMProvider):  # shim: complete(prompt, context, temperature=None, system_prompt=None) -> complete_text(...) with context appended, temperature ignored
  ```
  `model=None` means `settings.claude_quality_model`. Every call records `record_provider_call("claude", ok)` and, on success, `record_token_usage(model, usage.input_tokens, usage.output_tokens, agent)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_providers/test_claude.py
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel

from listingjet.providers.claude import ClaudeClient, ClaudeProvider, ProviderOutputError


class Out(BaseModel):
    room: str
    score: int


def _resp(parsed=None, text="hello", stop_reason="end_turn", in_tok=10, out_tok=5):
    return SimpleNamespace(
        parsed_output=parsed, stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok),
    )


@pytest.mark.asyncio
async def test_complete_json_uses_parse_and_records_usage():
    c = ClaudeClient(api_key="k")
    c._client.messages.parse = AsyncMock(return_value=_resp(parsed=Out(room="kitchen", score=80)))
    with patch("listingjet.providers.claude.record_token_usage") as rec, \
         patch("listingjet.providers.claude.settings") as s:
        s.claude_quality_model = "claude-sonnet-5"
        out = await c.complete_json("classify", Out, agent="test")
    assert out == Out(room="kitchen", score=80)
    kw = c._client.messages.parse.await_args.kwargs
    assert kw["model"] == "claude-sonnet-5" and kw["output_format"] is Out
    assert "temperature" not in kw and "thinking" not in kw
    rec.assert_called_once_with("claude-sonnet-5", 10, 5, "test")


@pytest.mark.asyncio
async def test_analyze_images_puts_image_blocks_before_text():
    c = ClaudeClient(api_key="k")
    c._client.messages.parse = AsyncMock(return_value=_resp(parsed=Out(room="bath", score=1)))
    with patch("listingjet.providers.claude.settings") as s:
        s.claude_fast_model = "claude-haiku-4-5"
        await c.analyze_images(["https://x/1.jpg", "https://x/2.jpg"], "which room", Out, model="claude-haiku-4-5")
    content = c._client.messages.parse.await_args.kwargs["messages"][0]["content"]
    assert [b["type"] for b in content] == ["image", "image", "text"]
    assert content[0]["source"] == {"type": "url", "url": "https://x/1.jpg"}


@pytest.mark.asyncio
async def test_none_parsed_output_raises_provider_output_error():
    c = ClaudeClient(api_key="k")
    c._client.messages.parse = AsyncMock(return_value=_resp(parsed=None, stop_reason="refusal"))
    with patch("listingjet.providers.claude.settings") as s:
        s.claude_quality_model = "claude-sonnet-5"
        with pytest.raises(ProviderOutputError):
            await c.complete_json("x", Out)


@pytest.mark.asyncio
async def test_shim_ignores_temperature_and_appends_context():
    p = ClaudeProvider(api_key="k")
    p._client.complete_text = AsyncMock(return_value="copy")
    out = await p.complete("write", {"beds": 3}, temperature=0.9, system_prompt="sys")
    assert out == "copy"
    kw = p._client.complete_text.await_args
    assert '"beds": 3' in kw.args[0] and kw.kwargs["system"] == "sys"
```

Look at the existing `tests/test_providers/test_claude.py` first and keep any test that still applies to the shim's public behaviour; delete the ones asserting `temperature` is sent.

- [ ] **Step 2: Run to verify RED** — `.venv/Scripts/python.exe -m pytest tests/test_providers/test_claude.py -q -p no:cacheprovider` (timeout 120000).

- [ ] **Step 3: Implement**

```python
# src/listingjet/providers/claude.py
"""Claude client: text, structured JSON, and image analysis on the anthropic 1.x SDK.

Model IDs come from settings (claude_fast_model for per-photo work,
claude_quality_model for copy and floorplans). Current models reject
sampling parameters, so temperature is never sent; tone lives in the system prompt.
"""
from __future__ import annotations

import json
import logging

import anthropic
from pydantic import BaseModel

from listingjet.config import settings
from listingjet.services.metrics import record_provider_call, record_token_usage

from .base import LLMProvider

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert real estate copywriter. Write compelling, accurate, and legally "
    "compliant listing descriptions. Avoid Fair Housing Act violations. Be specific about "
    "features, never generic."
)


class ProviderOutputError(RuntimeError):
    """The model returned no usable output (refusal, empty, or schema mismatch)."""


class ClaudeClient:
    def __init__(self, api_key: str | None = None):
        self._client = anthropic.AsyncAnthropic(api_key=api_key or settings.anthropic_api_key)

    async def _parse(self, *, messages, schema, system, model, max_tokens, agent):
        model = model or settings.claude_quality_model
        kwargs = {"model": model, "max_tokens": max_tokens, "messages": messages, "output_format": schema}
        if system:
            kwargs["system"] = system
        try:
            resp = await self._client.messages.parse(**kwargs)
        except Exception:
            record_provider_call("claude", False)
            raise
        record_provider_call("claude", True)
        usage = getattr(resp, "usage", None)
        if usage is not None:
            record_token_usage(model, usage.input_tokens, usage.output_tokens, agent)
        if getattr(resp, "parsed_output", None) is None:
            raise ProviderOutputError(f"no structured output (stop_reason={getattr(resp, 'stop_reason', None)!r})")
        return resp.parsed_output

    async def complete_json(self, prompt, schema, *, system=None, model=None, max_tokens=4096, agent=None):
        return await self._parse(messages=[{"role": "user", "content": prompt}], schema=schema,
                                 system=system, model=model, max_tokens=max_tokens, agent=agent)

    async def analyze_images(self, image_urls, prompt, schema, *, system=None, model=None, max_tokens=4096, agent=None):
        if not image_urls:
            raise ValueError("image_urls must be non-empty")
        content = [{"type": "image", "source": {"type": "url", "url": u}} for u in image_urls]
        content.append({"type": "text", "text": prompt})
        return await self._parse(messages=[{"role": "user", "content": content}], schema=schema,
                                 system=system, model=model, max_tokens=max_tokens, agent=agent)

    async def complete_text(self, prompt, *, system=None, model=None, max_tokens=4096, agent=None) -> str:
        model = model or settings.claude_quality_model
        kwargs = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
        if system:
            kwargs["system"] = system
        try:
            resp = await self._client.messages.create(**kwargs)
        except Exception:
            record_provider_call("claude", False)
            raise
        record_provider_call("claude", True)
        usage = getattr(resp, "usage", None)
        if usage is not None:
            record_token_usage(model, usage.input_tokens, usage.output_tokens, agent)
        if getattr(resp, "stop_reason", None) == "refusal":
            raise ProviderOutputError("model refused")
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


class ClaudeProvider(LLMProvider):
    """Legacy text interface used by content/social agents until Phase 5. `temperature` is ignored."""

    def __init__(self, api_key: str | None = None, client: ClaudeClient | None = None):
        self._client = client or ClaudeClient(api_key=api_key)

    async def complete(self, prompt, context, temperature=None, system_prompt=None) -> str:
        context_str = json.dumps(context, indent=2, default=str) if context else ""
        user = f"{prompt}\n\nContext:\n{context_str}" if context_str else prompt
        return await self._client.complete_text(user, system=system_prompt or DEFAULT_SYSTEM_PROMPT)
```

Settings (next to `anthropic_api_key`): `claude_fast_model: str = "claude-haiku-4-5"`, `claude_quality_model: str = "claude-sonnet-5"`. `help_agent.py`: replace the `_MODEL` constant with `settings.claude_quality_model` (read the file; if it builds its own `anthropic.AsyncAnthropic`, leave that but drop any `temperature` kwarg). `factory.py`: `get_claude()` returns `MockClaudeClient()` under `use_mock_providers` else `ClaudeClient()`; `get_llm_provider()` returns `ClaudeProvider(client=get_claude())` (mock under the flag stays `MockLLMProvider`). `mock.py` `MockClaudeClient`: `complete_text` returns a short deterministic string; `complete_json`/`analyze_images` return `schema.model_validate(_defaults_for(schema, seed))` where `_defaults_for` walks the schema's `model_fields`: `str` → `"mock"` (or the first enum literal), `int` → `1`, `float` → `0.5`, `bool` → `False`, `list` → `[]`, nested `BaseModel` → recurse; a hidden hook `MockClaudeClient.responses: dict[type, list[BaseModel]]` lets tests queue exact objects per schema. Export `ClaudeClient`, `ProviderOutputError`, `get_claude` from `providers/__init__.py`.

- [ ] **Step 4: GREEN + wider check** — `tests/test_providers tests/test_agents/test_content.py tests/test_agents/test_social_content.py` (timeout 300000). Ruff.
- [ ] **Step 5: Commit** — `feat(providers): ClaudeClient on anthropic 1.x with structured outputs; shim drops temperature`

---

### Task 2: Rates by model, usage recording

**Files:**
- Create: `src/listingjet/config/ai_rates.py`
- Modify: `src/listingjet/services/metrics.py` (`TOKEN_COSTS`/`PROVIDER_COSTS` imported from `ai_rates`; `record_token_usage(model_id, ...)` looks up by model id and logs a warning once per unknown id instead of silently skipping), `src/listingjet/providers/openai_dollhouse.py`, `_openai_edits.py` (call sites pass `"gpt-image-1.5"` as the model id label — check what they pass today)
- Test: `tests/test_services/test_metrics_logging.py` (extend), `tests/test_services/test_token_cost.py` (update)

```python
# src/listingjet/config/ai_rates.py
"""USD rates. Token rates are per 1M tokens (input, output); image rates per call.
Source: Anthropic price list cached 2026-06 in the claude-api skill; OpenAI image pricing
as observed in openai_dollhouse.py. Update here, nowhere else."""
TOKEN_RATES: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-5": (5.00, 25.00),
}
IMAGE_CALL_RATES: dict[str, float] = {
    "gpt-image-1.5": 0.05,   # 1536x1024 medium
}
LEGACY_CALL_RATES: dict[str, float] = {  # until Phase 6 replaces video
    "kling": 0.50,
}
```

Tests: `record_token_usage("claude-haiku-4-5", 1000, 100, "photo_analysis")` logs `EstimatedCost` `0.0015`; unknown id logs a warning and records tokens with cost 0.

- [ ] Steps: RED → implement → `tests/test_services` green → ruff → commit `feat(metrics): token rates keyed by model id`.

---

### Task 3: Migration 055 and the `VisionResult` columns

**Files:**
- Create: `alembic/versions/055_vision_result_analysis.py`
- Modify: `src/listingjet/models/vision_result.py`
- Test: `tests/test_models/test_vision_result_columns.py`

Columns (all nullable): `hero_score int`, `is_photo bool`, `is_empty_room bool`, `features jsonb`, `compliance jsonb`. Migration: `op.add_column` × 5; downgrade drops them. Test asserts the mapped columns exist and a row with `compliance={"people": True}` round-trips through `db_session`.

- [ ] Steps: RED → model + migration → `alembic heads` = 055; up/down/up on the dev DB → test green → ruff → commit `feat(db): vision_results analysis columns (055)`.

---

### Task 4: `PhotoAnalysisAgent` replaces vision tiers and compliance

**Files:**
- Create: `src/listingjet/agents/photo_analysis.py`, `src/listingjet/services/compliance.py`
- Modify: `src/listingjet/pipeline/definition.py` (steps `vision_tier1`, `vision_tier2`, `photo_compliance` → one `photo_analysis` requiring `ingestion`; `coverage`, `virtual_staging`, `floorplan` require `photo_analysis`; `distribution`'s requires drop `photo_compliance`), `src/listingjet/pipeline/steps.py`, `src/listingjet/api/image_edit.py` (auto-fix reads `compliance_report`), `src/listingjet/api/listings_workflow.py` (`/compliance` endpoint reads `compliance_report`; no agent run), `src/listingjet/providers/base.py` (drop `VisionProvider`, `VisionLabel`), `src/listingjet/providers/mock.py` (drop `MockVisionProvider`), `src/listingjet/providers/factory.py` (drop `get_vision_provider`, `get_tier2_vision_provider`), `src/listingjet/providers/__init__.py`, `src/listingjet/services/metrics.py` (`google_vision` rate removed), `src/listingjet/config/__init__.py` (drop `google_vision_api_key`; `validate_provider_keys` requires only `anthropic_api_key` + `openai_api_key`), `render.yaml`/`.env*.example` (drop `GOOGLE_VISION_API_KEY`), `tests/test_pipeline/test_definition.py`, `tests/test_pipeline/test_steps.py`, `tests/test_agents/test_pipeline.py`, `tests/test_api/test_listings.py`/`test_assets.py` if they reference compliance, `tests/test_config`
- Delete: `src/listingjet/agents/vision.py`, `src/listingjet/agents/photo_compliance.py`, `src/listingjet/providers/google_vision.py`, `src/listingjet/providers/openai_vision.py`, `tests/test_agents/test_vision.py`, `tests/test_agents/test_photo_compliance.py`, `tests/test_providers/test_google_vision.py`, `tests/test_providers/test_openai_vision.py`
- Test: `tests/test_agents/test_photo_analysis.py`, `tests/test_services/test_compliance.py`

**Interfaces:**
```python
class RoomLabel(str, Enum): exterior, drone, entryway, living_room, kitchen, dining_room, bedroom, primary_bedroom, bathroom, primary_bathroom, office, garage, basement, laundry, backyard, pool, patio, hallway, closet, other, floorplan, document, screenshot
class Compliance(BaseModel): people: bool; signage: bool; branding: bool; text_overlay: bool
class PhotoAnalysis(BaseModel):
    room: RoomLabel; is_interior: bool; is_photo: bool
    quality: int = Field(ge=0, le=100); hero_score: int = Field(ge=0, le=100)
    features: list[str] = []; is_empty_room: bool; compliance: Compliance; notes: str = ""
class PhotoAnalysisAgent(BaseAgent):
    agent_name = "photo_analysis"; requires_ai_consent = True
    def __init__(self, claude=None, storage=None, session_factory=None, concurrency: int = 8, per_image_timeout_s: float = 30.0)
    async def execute(ctx) -> {"analyzed": n, "failed": m, "flagged": k}
async def compliance_report(session, listing_id) -> dict   # same shape PhotoComplianceAgent returned: total_photos, compliant_count, flagged_count, all_compliant, decisions[], flagged_photos[]
```

Agent flow (load → call → save): session 1 loads assets in state `ingested` with `file_path`/`proxy_path`; outside any transaction, presign each proxy (or original) and `asyncio.gather` under `Semaphore(concurrency)` calling `claude.analyze_images([url], PROMPT, PhotoAnalysis, model=settings.claude_fast_model, agent="photo_analysis")` with `asyncio.wait_for(per_image_timeout_s)`; failures logged and collected; session 2 writes one `VisionResult(tier=1, room_label=room.value, is_interior, quality_score=quality, commercial_score=hero_score, hero_candidate=hero_score>=70, hero_explanation=notes, raw_labels=analysis.model_dump(), model_used=model, hero_score, is_photo, is_empty_room, features, compliance=compliance.model_dump())` per success (delete any prior tier-1 row for that asset first), emits `vision.tier1.completed` (keep the event name — SSE and health score key off it) and `photo_analysis.completed` with counts, and `photo_compliance.completed` with the report from `compliance_report()`. If more than half the assets failed (or all did), raise `RuntimeError` so the step fails and retries instead of silently proceeding (this closes the "vision swallows errors" carried item). `record_cost` is not called; usage comes from the client.

`PROMPT` (module constant): asks for exactly the schema fields, one photo, real-estate context, `is_photo=false` for floorplans/documents/screenshots, `is_empty_room=true` only for unfurnished interiors, compliance flags for people, yard/open-house signs, brokerage branding/watermarks, overlaid text. Keep it under 200 words.

`services/compliance.py::compliance_report` builds the old report dict from `VisionResult.compliance` of the listing's packaged assets (join `PackageSelection`; fall back to all analysed assets when nothing is packaged yet).

Tests: agent with `MockClaudeClient.responses[PhotoAnalysis] = [...]` queued per asset (3 assets: an exterior hero, an empty bedroom, a screenshot with text) → rows written with the mapped columns, `hero_candidate` true only for score ≥ 70, `is_photo` false for the screenshot; one asset whose call raises → still `analyzed == 2`; all raising → `RuntimeError`; `compliance_report` flags the text-overlay asset and returns `all_compliant False`. Use `make_session_factory(db_session)` and `patch("listingjet.agents.photo_analysis.get_storage")` like the old vision tests.

- [ ] Steps: RED → implement → delete old modules → grep gate `grep -rn "vision_tier\|VisionProvider\|VisionLabel\|google_vision\|openai_vision\|PhotoComplianceAgent\|get_tier2_vision_provider\|get_vision_provider" src tests` empty → full suite 0 failed → ruff → commit `feat(pipeline): one Claude pass per photo replaces vision tiers and compliance`.

---

### Task 5: Floorplan on Sonnet 5 with structured multi-image input

**Files:**
- Modify: `src/listingjet/agents/floorplan.py` (`FloorplanScene`/`FloorplanRoom` Pydantic models mirroring `FLOORPLAN_DOLLHOUSE_PROMPT`'s JSON; `self._claude = claude or get_claude()`; call `analyze_images(image_urls, prompt, FloorplanScene, model=settings.claude_quality_model, max_tokens=8000, agent="floorplan")`; drop `parse_llm_json`; `_find_floorplan_assets` uses `VisionResult.is_photo is False` OR the legacy label set), `tests/test_agents/test_floorplan.py` (queue a `FloorplanScene` on the mock; keep the 9 tests' intent)
- [ ] Steps: RED → implement → `tests/test_agents/test_floorplan.py tests/test_agents/test_dollhouse_render.py` green → ruff → commit `feat(floorplan): Sonnet 5 structured multi-image analysis`.

---

### Task 6: Virtual staging on empty rooms; OpenAI images consolidated

**Files:**
- Create: `src/listingjet/providers/openai_images.py` (`OpenAIImagesClient` with `edit(image_bytes, content_type, prompt, *, label, model="gpt-image-1.5", size, quality) -> bytes`, `edit_from_url(url, prompt, *, label) -> bytes`, `stage_room(image_url, room_type, style) -> bytes`, `remove_object(image_url, description) -> bytes`, `enhance(image_url, enhancement) -> bytes`, `render_dollhouse(floorplan_url, room_photo_urls, prompt=None) -> bytes`; raw httpx as today; records `record_image_call("gpt-image-1.5", label)` → add that helper to `services/metrics.py` using `IMAGE_CALL_RATES`)
- Modify: `src/listingjet/providers/openai_staging.py`, `openai_image_edit.py`, `openai_dollhouse.py` become thin subclasses/wrappers delegating to `OpenAIImagesClient` (keep class names so `factory.py`, `agents/dollhouse_render.py`, `api/image_edit.py` and their tests keep working); delete `_openai_edits.py` after moving its body; `src/listingjet/agents/virtual_staging.py` (candidates = `VisionResult.is_empty_room is True and room_label in _STAGEABLE_ROOMS`; if none → `{"skipped": True, "reason": "no_empty_rooms"}`)
- Test: `tests/test_providers/test_openai_images.py` (pytest-httpx: one edit call posts multipart to `/v1/images/edits` with the bearer key and returns decoded PNG bytes; a 400 raises `OpenAIEditError`), update `tests/test_providers/test_openai_edits.py`/`test_openai_dollhouse.py`, `tests/test_agents/test_virtual_staging.py` (create if absent: empty-room filter)
- [ ] Steps: RED → implement → `tests/test_providers tests/test_agents/test_dollhouse_render.py tests/test_agents/test_virtual_staging.py tests/test_api/test_dollhouse.py` green → ruff → commit `refactor(images): one OpenAI images client; staging only on empty rooms`.

---

### Task 7: End-to-end with mocks, optional real run, docs, PR

- [ ] Local e2e with mock providers exactly as in Phase 2's Task 10 (moto on :5000, `python -m listingjet.pipeline.worker`, `scripts/seed_sample_listing.py`), confirming `photo_analysis` writes one `vision_results` row per asset with `compliance` populated and the listing reaches `awaiting_review` then `delivered`.
- [ ] If `.env` contains a real `ANTHROPIC_API_KEY`, run ONE listing with `USE_MOCK_PROVIDERS=false` and record the `EstimatedCost` log lines (expected well under $1 for 12 photos on Haiku 4.5 + one Sonnet 5 floorplan call); otherwise state in the PR that the real run is pending keys.
- [ ] `CLAUDE.md`: providers row → "Claude (text + vision), OpenAI images, Canva"; migration head 055. `MASTER_TODO.md`: Phase 4 done, carried items updated (temperature and vision-error items closed).
- [ ] Full suite 0 failed; ruff; `alembic heads` = 055; push `feat/claude-providers`; `gh pr create --base chore/delete-and-flag --title "feat: Claude provider layer and one-pass photo analysis (phase 4)"` with body: what replaced what, per-listing call count before/after (~85 → ~25 + 1), the new columns, the compliance persistence, the `temperature` fix, the fail-if-most-photos-fail rule, e2e evidence, cost lines if a real run happened. End with the two attribution lines. Do not merge.
