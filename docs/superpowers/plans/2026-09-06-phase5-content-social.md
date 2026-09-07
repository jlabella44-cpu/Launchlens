# Phase 5: Content + Social in One Sonnet 5 Call — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `content` and `social_content` agents (two prompts, two Claude calls, regex JSON parsing, a temperature the SDK rejects) with one `ContentSocialAgent` that makes a single structured Sonnet 5 call, persists social rows the frontend can read, and serve the missing `/social-content` endpoint.

**Architecture:** One Pydantic schema (`ContentSocial`) drives `ClaudeClient.complete_json`. The agent loads everything in one session, closes it, calls Claude, runs the FHA post-check with at most one retry, then writes `SocialContent` rows (instagram, facebook, tiktok) in a fresh session and returns `{mls_safe, marketing, ...}` for `mls_export`. The legacy `LLMProvider` shim layer goes away with its last two callers.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async, Pydantic 2, anthropic 1.4.0 (`messages.parse(output_format=...)`), pytest + `MockClaudeClient`.

**Spec:** `docs/superpowers/specs/2026-09-05-free-tier-rework-design.md` — section "Phase 5: content and social".

## Global Constraints

- Branch `feat/content-social` off `feat/claude-providers` (PR #309). PR targets `feat/claude-providers`. Never push to `main`; never merge; never amend published commits.
- One Claude call per listing for copy + social (plus at most one FHA retry). Model `settings.claude_quality_model` (`claude-sonnet-5`), `max_tokens=8000`, `agent="content_social"`.
- No sampling parameters (temperature/top_p) are ever sent; tone lives in the system prompt only.
- Metadata sent to Claude passes through `services/pii_filter.sanitize_for_prompt`. Context is included in the prompt once (no separate `context` dict duplicated into the message).
- FHA post-check via `services/fha_filter.fha_check` on every generated text; on failure one retry with the FHA suffix; keep whichever passes, else the first with `fha_passed=False`. FHA regexes are English-only: skip the check (pass) when `language != "en"`.
- Agents never hold a DB transaction open across a Claude call (load → call → save).
- `SocialContent` rows keep today's shape: `platform` in {`instagram`, `facebook`, `tiktok`}, `caption` = JSON list of `{"style","caption"}` hooks for instagram/facebook, plain text for tiktok, `hashtags` list only on instagram, `cta` on instagram/facebook.
- Every Bash call passes an explicit timeout; never two pytest processes at once; full suite must be 0 failed; `ruff check src tests alembic` clean.
- Commit trailer on every commit:
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01FN81v1ehP7Snv3UsWaRf9D
  ```

---

## File map

| File | Responsibility |
|---|---|
| `src/listingjet/agents/content_social.py` (new) | Schema + `ContentSocialAgent` |
| `src/listingjet/agents/content.py`, `social_content.py` (delete) | replaced |
| `src/listingjet/pipeline/definition.py`, `steps.py` | `content_social` step; `mls_export` reads its result |
| `src/listingjet/api/social_content.py` (new) | `GET /listings/{id}/social-content` |
| `src/listingjet/main.py` | register the router |
| `src/listingjet/api/sse.py`, `api/listings_workflow.py`, `frontend/src/lib/use-listing-events.ts` | event names |
| `src/listingjet/providers/base.py`, `claude.py`, `mock.py`, `factory.py`, `__init__.py`, `canva.py`, `agents/base.py` | remove `LLMProvider`/`ClaudeProvider`/`MockLLMProvider`/`get_llm_provider`/`parse_llm_json` |
| tests | `tests/test_agents/test_content_social.py`, `tests/test_api/test_social_content.py`; delete `test_content.py`, `test_social_content.py`; update `test_pipeline.py`, `tests/chaos/test_provider_failures.py`, `tests/test_pipeline/*`, `tests/test_providers/test_claude.py` |

---

### Task 1: `ContentSocialAgent`

**Files:**
- Create: `src/listingjet/agents/content_social.py`
- Test: `tests/test_agents/test_content_social.py`

**Interfaces:**
- Consumes: `listingjet.providers.factory.get_claude()`; `ClaudeClient.complete_json(prompt, schema, *, system, model, max_tokens, agent) -> BaseModel`; `MockClaudeClient.responses[schema]: list[BaseModel]`; `VisionResult.hero_score`, `.features` (list[str]), `.room_label`, `.is_photo`; `PackageSelection.position`; `BrandKit.voice_samples`; `Tenant.preferred_language`; `PropertyData` (walk_score, lifestyle_tags, nearby_amenities, school_ratings); `fha_check(dict) -> FHAResult(passed, violations)`; `sanitize_for_prompt(dict)`.
- Produces: `ContentSocialAgent(claude=None, session_factory=None)`, `agent_name = "content_social"`, `requires_ai_consent = True`; `execute(ctx) -> {"mls_safe": str, "marketing": str, "fha_passed": bool, "language": str, "platforms": ["instagram","facebook","tiktok"]}`; event `content_social.completed` with payload `{fha_passed, language, platforms, has_voice_samples, market_context}`; schema classes `Hook`, `InstagramCopy`, `FacebookCopy`, `ContentSocial`; `_tone_to_config(intensity: int) -> str` (system prompt key only).

- [ ] **Step 1: Write the failing tests** — `tests/test_agents/test_content_social.py`

```python
import json

import pytest
from sqlalchemy import select

from listingjet.agents.base import AgentContext
from listingjet.agents.content_social import (
    ContentSocial, ContentSocialAgent, FacebookCopy, Hook, InstagramCopy, _tone_to_config,
)
from listingjet.models.outbox import Outbox
from listingjet.models.social_content import SocialContent
from listingjet.models.vision_result import VisionResult
from listingjet.providers.mock import MockClaudeClient
from tests.test_agents.conftest import make_session_factory

STYLES = ["storyteller", "data_driven", "luxury_minimalist", "urgency", "lifestyle"]


def _hooks(text: str) -> list[Hook]:
    return [Hook(style=s, caption=f"{s}: {text}") for s in STYLES]


def _copy(mls="Three-bedroom home with a renovated kitchen.", marketing="Sunlit rooms and a chef's kitchen."):
    return ContentSocial(
        mls_safe=mls,
        marketing=marketing,
        instagram=InstagramCopy(hooks=_hooks(marketing), hashtags=["#justlisted"] * 20, cta="Link in bio"),
        facebook=FacebookCopy(hooks=_hooks(marketing), cta="Book a showing"),
        tiktok_caption="Tour this one before it's gone.",
    )


async def _add_vr(db_session, asset_id, room_label="kitchen", hero_score=80, features=None):
    vr = VisionResult(
        asset_id=asset_id, tier=1, room_label=room_label, is_interior=True,
        quality_score=hero_score, commercial_score=hero_score, hero_score=hero_score,
        hero_candidate=hero_score >= 70, is_photo=True,
        features=features or ["quartz counters", "island"], raw_labels={}, model_used="claude-haiku-4-5",
    )
    db_session.add(vr)
    await db_session.flush()


def _agent(db_session, mock):
    return ContentSocialAgent(claude=mock, session_factory=make_session_factory(db_session))


@pytest.mark.asyncio
async def test_one_call_returns_copy_and_writes_three_social_rows(db_session, listing, assets):
    for a in assets:
        await _add_vr(db_session, a.id)
    mock = MockClaudeClient()
    mock.responses[ContentSocial] = [_copy()]
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    result = await _agent(db_session, mock).execute(ctx)

    assert result["mls_safe"].startswith("Three-bedroom")
    assert result["marketing"]
    assert result["fha_passed"] is True
    assert result["platforms"] == ["instagram", "facebook", "tiktok"]
    rows = (await db_session.execute(
        select(SocialContent).where(SocialContent.listing_id == listing.id).order_by(SocialContent.platform)
    )).scalars().all()
    by_platform = {r.platform: r for r in rows}
    assert set(by_platform) == {"facebook", "instagram", "tiktok"}
    ig_hooks = json.loads(by_platform["instagram"].caption)
    assert [h["style"] for h in ig_hooks] == STYLES
    assert len(by_platform["instagram"].hashtags) == 20
    assert by_platform["instagram"].cta == "Link in bio"
    assert by_platform["facebook"].hashtags is None
    assert by_platform["tiktok"].caption == "Tour this one before it's gone."


@pytest.mark.asyncio
async def test_call_uses_quality_model_and_8000_tokens(db_session, listing, assets, monkeypatch):
    mock = MockClaudeClient()
    mock.responses[ContentSocial] = [_copy()]
    seen = {}
    orig = mock.complete_json

    async def spy(prompt, schema, **kw):
        seen.update(kw, prompt=prompt, schema=schema)
        return await orig(prompt, schema, **kw)

    monkeypatch.setattr(mock, "complete_json", spy)
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await _agent(db_session, mock).execute(ctx)

    assert seen["schema"] is ContentSocial
    assert seen["model"] == "claude-sonnet-5"
    assert seen["max_tokens"] == 8000
    assert seen["agent"] == "content_social"
    assert "temperature" not in seen
    assert seen["system"]  # tone system prompt present


@pytest.mark.asyncio
async def test_fha_violation_triggers_one_retry(db_session, listing, assets):
    bad = _copy(mls="Perfect for families in a safe neighborhood.")
    good = _copy()
    mock = MockClaudeClient()
    mock.responses[ContentSocial] = [bad, good]
    calls = []
    orig = mock.complete_json

    async def spy(prompt, schema, **kw):
        calls.append(prompt)
        return await orig(prompt, schema, **kw)

    mock.complete_json = spy
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await _agent(db_session, mock).execute(ctx)

    assert len(calls) == 2
    assert "Fair Housing Act" in calls[1]
    assert result["fha_passed"] is True
    assert result["mls_safe"] == good.mls_safe


@pytest.mark.asyncio
async def test_two_fha_failures_keep_first_and_flag(db_session, listing, assets):
    bad1 = _copy(mls="Great schools nearby.")
    bad2 = _copy(mls="Family friendly street.")
    mock = MockClaudeClient()
    mock.responses[ContentSocial] = [bad1, bad2]
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await _agent(db_session, mock).execute(ctx)
    assert result["fha_passed"] is False
    assert result["mls_safe"] == bad1.mls_safe


@pytest.mark.asyncio
async def test_non_english_skips_fha(db_session, listing, assets):
    listing.metadata_ = {**(listing.metadata_ or {}), "language": "es"}
    await db_session.flush()
    mock = MockClaudeClient()
    mock.responses[ContentSocial] = [_copy(mls="Perfecto para familias.")]
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await _agent(db_session, mock).execute(ctx)
    assert result["language"] == "es"
    assert result["fha_passed"] is True


@pytest.mark.asyncio
async def test_rerun_replaces_social_rows(db_session, listing, assets):
    mock = MockClaudeClient()
    mock.responses[ContentSocial] = [_copy(), _copy(marketing="Second pass.")]
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    agent = _agent(db_session, mock)
    await agent.execute(ctx)
    await agent.execute(ctx)
    count = (await db_session.execute(
        select(SocialContent).where(SocialContent.listing_id == listing.id)
    )).scalars().all()
    assert len(count) == 3


@pytest.mark.asyncio
async def test_emits_completed_event(db_session, listing, assets):
    mock = MockClaudeClient()
    mock.responses[ContentSocial] = [_copy()]
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await _agent(db_session, mock).execute(ctx)
    evt = (await db_session.execute(
        select(Outbox).where(Outbox.event_type == "content_social.completed")
    )).scalars().first()
    assert evt is not None
    assert evt.payload["platforms"] == ["instagram", "facebook", "tiktok"]


@pytest.mark.asyncio
async def test_prompt_contains_features_and_no_pii(db_session, listing, assets):
    listing.metadata_ = {**(listing.metadata_ or {}), "agent_email": "x@y.z", "owner_name": "Pat"}
    await db_session.flush()
    for a in assets:
        await _add_vr(db_session, a.id, features=["vaulted ceilings"])
    mock = MockClaudeClient()
    mock.responses[ContentSocial] = [_copy()]
    seen = {}
    orig = mock.complete_json

    async def spy(prompt, schema, **kw):
        seen["prompt"] = prompt
        return await orig(prompt, schema, **kw)

    mock.complete_json = spy
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await _agent(db_session, mock).execute(ctx)
    assert "vaulted ceilings" in seen["prompt"]
    assert "x@y.z" not in seen["prompt"] and "Pat" not in seen["prompt"]


def test_tone_to_config():
    assert _tone_to_config(0) == "utility"
    assert _tone_to_config(20) == "utility"
    assert _tone_to_config(50) == "balanced"
    assert _tone_to_config(90) == "high_flair"
```

Check `tests/test_agents/conftest.py` for the `listing`/`assets` fixture names and the `Outbox` model path (`grep -rn "class Outbox" src`). If `Outbox.payload` is named differently, adjust the event test.

- [ ] **Step 2: Run to verify RED** — `.venv/Scripts/python.exe -m pytest tests/test_agents/test_content_social.py -q -p no:cacheprovider` → `ModuleNotFoundError: listingjet.agents.content_social`.

- [ ] **Step 3: Implement** `src/listingjet/agents/content_social.py`

```python
"""Listing copy and social captions in one Sonnet 5 call."""
import json
import logging

from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from listingjet.config import settings
from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.brand_kit import BrandKit
from listingjet.models.listing import Listing
from listingjet.models.package_selection import PackageSelection
from listingjet.models.property_data import PropertyData
from listingjet.models.social_content import SocialContent
from listingjet.models.tenant import Tenant
from listingjet.models.vision_result import VisionResult
from listingjet.providers.factory import get_claude
from listingjet.services.fha_filter import fha_check
from listingjet.services.pii_filter import sanitize_for_prompt

from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)

HOOK_STYLES = ("storyteller", "data_driven", "luxury_minimalist", "urgency", "lifestyle")
PLATFORMS = ["instagram", "facebook", "tiktok"]


class Hook(BaseModel):
    style: str = Field(description="one of: " + ", ".join(HOOK_STYLES))
    caption: str = ""


class InstagramCopy(BaseModel):
    hooks: list[Hook] = Field(default_factory=list, description="exactly five hooks, one per style, max 2200 chars each")
    hashtags: list[str] = Field(default_factory=list, description="20-30 hashtags, each starting with #")
    cta: str = "Link in bio for details"


class FacebookCopy(BaseModel):
    hooks: list[Hook] = Field(default_factory=list, description="exactly five hooks, one per style, max 500 chars each")
    cta: str = "Schedule a showing today"


class ContentSocial(BaseModel):
    mls_safe: str = Field(default="", description="2-3 sentences, factual only, no agent promotion, no personality")
    marketing: str = Field(default="", description="2-3 sentences, compelling, personality allowed, FHA compliant")
    instagram: InstagramCopy = Field(default_factory=InstagramCopy)
    facebook: FacebookCopy = Field(default_factory=FacebookCopy)
    tiktok_caption: str = Field(default="", description="one punchy caption under 150 chars, no hashtags")


_LANGUAGE_NAMES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "pt": "Portuguese", "zh": "Chinese", "ja": "Japanese", "ko": "Korean",
    "it": "Italian", "ar": "Arabic",
}

_TONE_SYSTEM_PROMPTS = {
    "utility": (
        "You are a factual real estate copywriter. Focus strictly on facts and MLS compliance. "
        "No personality, no flair, no adjectives beyond what the photos show. Be concise."
    ),
    "balanced": (
        "You are a professional real estate copywriter. Use any example descriptions as a guide "
        "for voice and style, but adapt naturally to this property's features. "
        "Be compelling but grounded in the actual photos."
    ),
    "high_flair": (
        "You are a luxury real estate copywriter channeling this agent's signature voice. "
        "Deeply mimic the vocabulary, rhythm, and cadence of the examples. "
        "Be creative, punchy, and bold — make this listing stand out."
    ),
}

_MARKET_PROMPTS = {
    "buyers_market": "Market context: BUYER'S MARKET. Emphasize investment potential, value, and negotiation flexibility.",
    "hot_market": "Market context: HOT MARKET. Create urgency. Emphasize demand, multiple offers expected, act fast.",
    "spring_refresh": "Market context: SPRING REFRESH. Highlight fresh starts, curb appeal, outdoor living, natural light.",
    "investment": "Market context: INVESTMENT OPPORTUNITY. Focus on ROI, rental potential, cap rate, location fundamentals.",
}

_FHA_RULES = (
    "Never use Fair Housing Act prohibited language: no 'perfect for families', 'family friendly', "
    "'safe neighborhood', 'great schools', 'exclusive community', no references to religion, "
    "national origin, disability, or familial status."
)

_FHA_RETRY_SUFFIX = (
    "\n\nIMPORTANT: The previous attempt contained language that may violate the Fair Housing Act. "
    "Rewrite every field without referencing families, schools, neighborhood safety, or religion."
)

_PROMPT = """\
Write listing copy and social captions for this property.
{fha_rules}
{language_instruction}
Property details:
{metadata}

Top features identified from the photos:
{photo_features}

Hero photo: {hero}
{voice_section}{market_section}{neighborhood}
Produce:
- mls_safe: 2-3 sentences, factual only, no agent promotion.
- marketing: 2-3 sentences, compelling, still FHA compliant.
- instagram: five hooks (styles storyteller, data_driven, luxury_minimalist, urgency, lifestyle), 20-30 hashtags, a CTA.
- facebook: five hooks in the same styles (max 500 chars each), a CTA.
- tiktok_caption: one punchy caption under 150 characters.
"""


def _tone_to_config(intensity: int) -> str:
    """Map the 0-100 tone slider to a system prompt key."""
    if intensity <= 20:
        return "utility"
    if intensity <= 60:
        return "balanced"
    return "high_flair"


def _fha_texts(copy: ContentSocial) -> dict[str, str]:
    texts = {"mls_safe": copy.mls_safe, "marketing": copy.marketing, "tiktok": copy.tiktok_caption,
             "ig_cta": copy.instagram.cta, "fb_cta": copy.facebook.cta}
    for i, h in enumerate(copy.instagram.hooks):
        texts[f"ig_{i}"] = h.caption
    for i, h in enumerate(copy.facebook.hooks):
        texts[f"fb_{i}"] = h.caption
    return texts


def _neighborhood(prop: PropertyData | None) -> str:
    if not prop:
        return ""
    parts = []
    if isinstance(prop.walk_score, int) and prop.walk_score >= 70:
        parts.append(f"Walk Score: {prop.walk_score}/100 (very walkable)")
    if prop.lifestyle_tags:
        parts.append(f"Neighborhood: {', '.join(prop.lifestyle_tags)}")
    if prop.nearby_amenities:
        names = [a["name"] for a in prop.nearby_amenities[:3] if isinstance(a, dict) and a.get("name")]
        if names:
            parts.append(f"Nearby: {', '.join(names)}")
    return "\n\nNeighborhood context:\n" + "\n".join(f"- {p}" for p in parts) if parts else ""


class ContentSocialAgent(BaseAgent):
    agent_name = "content_social"
    requires_ai_consent = True

    def __init__(self, claude=None, session_factory=None):
        self._claude = claude or get_claude()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        # ---- load (one session, closed before the Claude call) ----
        async with self.session_scope(context) as (session, listing_id, tenant_id):
            listing = await session.get(Listing, listing_id)
            meta = dict(listing.metadata_ or {})
            address = dict(listing.address or {})

            vrs = (await session.execute(
                select(VisionResult)
                .join(Asset, VisionResult.asset_id == Asset.id)
                .where(Asset.listing_id == listing_id, VisionResult.tier == 1, VisionResult.is_photo.isnot(False))
                .order_by(VisionResult.hero_score.desc().nullslast())
                .limit(8)
            )).scalars().all()
            feature_lines = []
            for vr in vrs:
                feats = ", ".join(vr.features or [])
                feature_lines.append(f"- {vr.room_label or 'photo'}: {feats}" if feats else f"- {vr.room_label or 'photo'}")

            hero_vr = (await session.execute(
                select(VisionResult)
                .join(Asset, VisionResult.asset_id == Asset.id)
                .join(PackageSelection, PackageSelection.asset_id == Asset.id)
                .where(PackageSelection.listing_id == listing_id, PackageSelection.position == 0,
                       VisionResult.tier == 1)
                .limit(1)
            )).scalars().first()
            hero = f"{hero_vr.room_label} (hero score {hero_vr.hero_score})" if hero_vr else "exterior"

            brand_kit = (await session.execute(
                select(BrandKit).where(BrandKit.tenant_id == tenant_id).limit(1)
            )).scalar_one_or_none()
            voice_samples = list((brand_kit.voice_samples or [])[:3]) if brand_kit else []

            language = meta.get("language", "en")
            if language == "en":
                tenant = await session.get(Tenant, tenant_id)
                if tenant and tenant.preferred_language and tenant.preferred_language != "en":
                    language = tenant.preferred_language

            prop = (await session.execute(
                select(PropertyData).where(PropertyData.listing_id == listing_id)
            )).scalar_one_or_none()
            neighborhood = _neighborhood(prop)

        # ---- build prompt ----
        safe_meta = sanitize_for_prompt(meta)
        safe_meta["address"] = {k: address.get(k, "") for k in ("street", "city", "state")}
        market_context = meta.get("market_context", "")
        market_section = ("\n\n" + _MARKET_PROMPTS[market_context]) if market_context in _MARKET_PROMPTS else ""
        voice_section = ""
        if voice_samples:
            voice_section = "\n\nMatch the voice and style of these example descriptions from this agent:\n" + "".join(
                f"\nExample {i}: {s}\n" for i, s in enumerate(voice_samples, 1)
            )
        lang_name = _LANGUAGE_NAMES.get(language, language)
        language_instruction = (
            f"Write ALL text in {lang_name.upper()}. Do not include any English text."
            if language != "en" else ""
        )
        system = _TONE_SYSTEM_PROMPTS[_tone_to_config(int(meta.get("tone_intensity", 50)))]
        prompt = _PROMPT.format(
            fha_rules=_FHA_RULES,
            language_instruction=language_instruction,
            metadata=json.dumps(safe_meta, default=str),
            photo_features="\n".join(feature_lines) or "- modern interior",
            hero=hero,
            voice_section=voice_section,
            market_section=market_section,
            neighborhood=neighborhood,
        )

        # ---- call (no DB session open) ----
        copy = await self._call(prompt, system)
        fha_passed = True
        if language == "en":
            first = copy
            result = fha_check(_fha_texts(copy))
            if not result.passed:
                logger.info("content_social FHA violations listing=%s: %s — retrying", listing_id, result.violations)
                copy = await self._call(prompt + _FHA_RETRY_SUFFIX, system)
                result = fha_check(_fha_texts(copy))
                if not result.passed:
                    logger.warning("content_social FHA retry still failing listing=%s: %s", listing_id, result.violations)
                    copy = first
            fha_passed = result.passed

        # ---- save ----
        async with self.session_scope(context) as (session, listing_id, tenant_id):
            await session.execute(delete(SocialContent).where(SocialContent.listing_id == listing_id))
            session.add_all([
                SocialContent(
                    listing_id=listing_id, tenant_id=tenant_id, platform="instagram",
                    caption=json.dumps([h.model_dump() for h in copy.instagram.hooks]),
                    hashtags=copy.instagram.hashtags, cta=copy.instagram.cta,
                ),
                SocialContent(
                    listing_id=listing_id, tenant_id=tenant_id, platform="facebook",
                    caption=json.dumps([h.model_dump() for h in copy.facebook.hooks]),
                    hashtags=None, cta=copy.facebook.cta,
                ),
                SocialContent(
                    listing_id=listing_id, tenant_id=tenant_id, platform="tiktok",
                    caption=copy.tiktok_caption, hashtags=None, cta=None,
                ),
            ])
            await self.emit(session, context, "content_social.completed", {
                "fha_passed": fha_passed,
                "language": language,
                "platforms": PLATFORMS,
                "has_voice_samples": bool(voice_samples),
                "market_context": market_context or None,
            })

        return {
            "mls_safe": copy.mls_safe,
            "marketing": copy.marketing,
            "fha_passed": fha_passed,
            "language": language,
            "platforms": PLATFORMS,
        }

    async def _call(self, prompt: str, system: str) -> ContentSocial:
        return await self._claude.complete_json(
            prompt, ContentSocial,
            system=system,
            model=settings.claude_quality_model,
            max_tokens=8000,
            agent=self.agent_name,
        )
```

Check `session_scope` in `agents/base.py`: it yields `(session, listing_id, tenant_id)` with UUIDs already parsed and commits on exit. `SocialContent.tenant_id` must be the tenant UUID (as `listing.tenant_id` today). `VisionResult.is_photo.isnot(False)` keeps NULL rows (pre-055 data). `hashtags` is a JSONB column — a list is fine.

- [ ] **Step 4: Run to verify GREEN** — same command; all 9 pass.
- [ ] **Step 5: Ruff** — `.venv/Scripts/ruff.exe check src/listingjet/agents/content_social.py tests/test_agents/test_content_social.py`.
- [ ] **Step 6: Commit** — `feat(agents): ContentSocialAgent — copy and social captions in one Sonnet 5 call`.

---

### Task 2: Pipeline rewiring, deletions, event names

**Files:**
- Modify: `src/listingjet/pipeline/definition.py:36-41`, `src/listingjet/pipeline/steps.py:13,27,61,145,147`, `src/listingjet/api/sse.py:27-31`, `src/listingjet/api/listings_workflow.py:353-358`, `frontend/src/lib/use-listing-events.ts:73`
- Delete: `src/listingjet/agents/content.py`, `src/listingjet/agents/social_content.py`, `tests/test_agents/test_content.py`, `tests/test_agents/test_social_content.py`
- Modify tests: `tests/test_pipeline/test_definition.py`, `tests/test_pipeline/test_steps.py`, `tests/test_pipeline/test_runner_scale.py`, `tests/test_agents/test_pipeline.py`, `tests/chaos/test_provider_failures.py`

**Interfaces:**
- Consumes: `ContentSocialAgent` (Task 1); `ctx.results` keyed by step name.
- Produces: pipeline step `content_social` (requires `await_review`); `brand` requires `content_social`; `mls_export` requires `("content_social", "brand")`; `distribution` requires `("mls_export", "social_cuts")`; `run_mls_export` passes `ctx.results.get("content_social")`; SSE event `content_social.completed`.

- [ ] **Step 1: Update definition tests first** — in `tests/test_pipeline/test_definition.py`: step count `21 → 20`; `STEP_INDEX["content_social"].requires == ("await_review",)`; `STEP_INDEX["brand"].requires == ("content_social",)`; `STEP_INDEX["mls_export"].requires == ("content_social", "brand")`; `STEP_INDEX["distribution"].requires == ("mls_export", "social_cuts")`; replace `"content"` with `"content_social"` in the required-name and ordering assertions. In `tests/test_pipeline/test_steps.py:19-30` rename the results key to `"content_social"`. In `test_runner_scale.py` replace `"content"` step names with `"content_social"`, update the docstring and any numeric assertion that counted 11 post-approval rows (now 10: content_social, brand, social_cuts, mls_export, distribution, microsite, learning, social_event, health_score, performance_intelligence) — read the test body and adjust the arithmetic (e.g. 550 → 500) so the scenario still fills the window (raise the parked-listing count to 55 if needed).
- [ ] **Step 2: Run RED** — `.venv/Scripts/python.exe -m pytest tests/test_pipeline/test_definition.py tests/test_pipeline/test_steps.py -q -p no:cacheprovider`.
- [ ] **Step 3: Implement**
  - `definition.py`: replace lines 36-41 with
    ```python
    Step("content_social", requires=("await_review",)),
    Step("brand", requires=("content_social",), optional=True),
    Step("social_cuts", requires=("video", "await_review"), optional=True),
    Step("mls_export", requires=("content_social", "brand"), timeout_s=15 * _MIN),
    Step("distribution", requires=("mls_export", "social_cuts")),
    ```
  - `steps.py`: import `ContentSocialAgent`; `run_mls_export` uses `ctx.results.get("content_social") or {}`; `STEP_FUNCTIONS["content_social"] = _agent_step(ContentSocialAgent)`; remove `content` and `social_content` entries and imports.
  - `api/sse.py`: replace `"content.completed"` and `"social_content.completed"` with `"content_social.completed"`.
  - `api/listings_workflow.py` legacy `pipeline_steps` list: replace `"content", "brand", "social_content"` with `"content_social", "brand"`; also drop the dead `"compliance"` entry (Phase 4 deferred minor).
  - `frontend/src/lib/use-listing-events.ts:73`: same event rename. Run `cd frontend && npx tsc --noEmit` (timeout 300000) to confirm no type break.
  - Delete the two old agents and their tests.
  - `tests/test_agents/test_pipeline.py`: replace the `ContentAgent` step with `ContentSocialAgent(claude=mock_claude, session_factory=sf)` where `mock_claude = MockClaudeClient()` with a queued `ContentSocial`; if the sequence later ran `SocialContentAgent`, drop that step.
  - `tests/chaos/test_provider_failures.py` (`TestContentAgentLLMFailure`): port to `ContentSocialAgent` with a claude stub whose `complete_json` raises; the assertions (error propagates, no `SocialContent` rows written, no completion event) keep their intent.
- [ ] **Step 4: GREEN** — `.venv/Scripts/python.exe -m pytest tests/test_pipeline tests/test_agents/test_pipeline.py tests/chaos tests/test_api/test_sse.py -q -p no:cacheprovider` (timeout 300000; drop non-existent paths).
- [ ] **Step 5: Grep gate** — `grep -rn "ContentAgent\b\|SocialContentAgent\|agents\.content\b\|agents\.social_content\|\"social_content\.completed\"\|\"content\.completed\"" src tests frontend/src --include=*.py --include=*.ts --include=*.tsx` must be empty. (`tenant_settings.py` `"social_content"` plan-limit key and `credits.py` `social_content_pack` are billing labels, not steps: leave them.)
- [ ] **Step 6: Commit** — `feat(pipeline): content_social step replaces content + social_content`.

---

### Task 3: Remove the LLMProvider shim layer

**Files:**
- Modify: `src/listingjet/providers/base.py` (drop `LLMProvider`), `providers/claude.py` (drop `ClaudeProvider`), `providers/mock.py` (drop `MockLLMProvider`), `providers/factory.py` (drop `get_llm_provider`; `get_template_provider` no longer passes `llm_provider`), `providers/__init__.py`, `providers/canva.py:24-26` (drop the unused `llm_provider` param and `self._llm`), `src/listingjet/agents/base.py` (drop `parse_llm_json` if no caller remains — `grep -rn parse_llm_json src`), `tests/test_providers/test_claude.py` (remove shim tests), any test constructing `CanvaTemplateProvider(..., llm_provider=...)` or `MockLLMProvider`.

**Interfaces:**
- Consumes: nothing new.
- Produces: `providers.__init__` exports `ImageEditProvider, TemplateProvider, VirtualStagingProvider, get_claude, get_image_edit_provider, get_virtual_staging_provider, get_template_provider`.

- [ ] **Step 1: Grep callers** — `grep -rn "get_llm_provider\|ClaudeProvider\|MockLLMProvider\|LLMProvider\b\|parse_llm_json\|llm_provider" src tests --include=*.py`. Expect: factory, base, claude, mock, `__init__`, canva, test_claude, and possibly a canva test.
- [ ] **Step 2: Remove** each; keep `ClaudeClient`, `ProviderOutputError`, `MockClaudeClient` untouched. `help_agent.py` already uses `get_claude()` (verify).
- [ ] **Step 3: Gate** — the grep from Step 1 returns nothing; `.venv/Scripts/python.exe -m pytest tests/test_providers tests/test_agents -q -p no:cacheprovider` (timeout 300000) green; ruff clean.
- [ ] **Step 4: Commit** — `refactor(providers): drop the LLMProvider shim; ClaudeClient is the only text interface`.

---

### Task 4: `GET /listings/{id}/social-content`

**Files:**
- Create: `src/listingjet/api/social_content.py`
- Modify: `src/listingjet/main.py` (include router; find where `listings_core.router` is included and add next to it — confirm the prefix so the final path is `/listings/{listing_id}/social-content`)
- Test: `tests/test_api/test_social_content.py`

**Interfaces:**
- Consumes: `SocialContent` rows as written by Task 1; `get_current_user`, `get_db` from `api/deps.py` (check names in `listings_core.py` imports).
- Produces: JSON `{"instagram_captions": {style: caption}, "facebook_captions": {style: caption}, "tiktok_caption": str|null, "hashtags": [str], "cta": {"instagram": str|null, "facebook": str|null}, "generated": bool}` — matches `frontend/src/components/listings/social-post-hub.tsx` `SocialContent` interface (`instagram_captions`, `facebook_captions`, `hashtags`; extra keys are ignored).

- [ ] **Step 1: Failing test** — `tests/test_api/test_social_content.py`. Look at an existing API test (e.g. `tests/test_api/test_dollhouse.py`) for the client/auth fixtures and copy that setup. Cases:
  1. listing with the three rows → 200, `instagram_captions["storyteller"]` equals the storyteller hook caption, `facebook_captions` has 5 keys, `hashtags` is the list, `tiktok_caption` set, `generated is True`.
  2. listing with no rows → 200, all maps empty, `generated is False`.
  3. listing of another tenant → 404.
  4. legacy row whose `caption` is plain text (not JSON) → `instagram_captions == {"storyteller": "<text>"}` (do not 500).
- [ ] **Step 2: RED**, then implement:

```python
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user, get_db
from listingjet.models.listing import Listing
from listingjet.models.social_content import SocialContent
from listingjet.models.user import User

router = APIRouter(prefix="/listings", tags=["social-content"])


def _captions(raw: str) -> dict[str, str]:
    try:
        hooks = json.loads(raw)
    except (TypeError, ValueError):
        return {"storyteller": raw} if raw else {}
    if isinstance(hooks, list):
        return {h["style"]: h["caption"] for h in hooks if isinstance(h, dict) and h.get("style")}
    return {"storyteller": raw}


@router.get("/{listing_id}/social-content")
async def get_social_content(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = (await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == current_user.tenant_id)
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    rows = (await db.execute(
        select(SocialContent).where(SocialContent.listing_id == listing_id)
    )).scalars().all()
    by_platform = {r.platform: r for r in rows}
    ig, fb, tt = by_platform.get("instagram"), by_platform.get("facebook"), by_platform.get("tiktok")
    return {
        "instagram_captions": _captions(ig.caption) if ig else {},
        "facebook_captions": _captions(fb.caption) if fb else {},
        "tiktok_caption": tt.caption if tt else None,
        "hashtags": list(ig.hashtags or []) if ig else [],
        "cta": {"instagram": ig.cta if ig else None, "facebook": fb.cta if fb else None},
        "generated": bool(rows),
    }
```

- [ ] **Step 3: GREEN** — `.venv/Scripts/python.exe -m pytest tests/test_api/test_social_content.py -q -p no:cacheprovider`; ruff.
- [ ] **Step 4: Commit** — `feat(api): GET /listings/{id}/social-content for the social hub`.

---

### Task 5: E2E with mocks, docs, PR

- [ ] Mock e2e exactly as Phase 4 Task 7 (moto on :5000, `python -m listingjet.pipeline.worker`, `scripts/seed_sample_listing.py`, approve via `complete_review`): confirm `content_social` reaches `done`, exactly three `social_contents` rows exist for the listing, `mls_export` is `done`, listing `delivered`. Curl-free check of the endpoint: a 6-line python using `httpx.AsyncClient(app=...)`or the test client is fine — or rely on the API test from Task 4.
- [ ] `CLAUDE.md`: pipeline step list/mention of `content`/`social_content` → `content_social`; providers row unchanged. `MASTER_TODO.md`: Phase 4 row gets `#309`; Phase 5 row → `feat/content-social` / PR #, "done, awaiting merge".
- [ ] Full suite 0 failed (timeout 600000), ruff clean, `alembic heads` still `055_vision_result_analysis` (no migration this phase).
- [ ] Push `feat/content-social`; `gh pr create --base feat/claude-providers --title "feat: one-call content + social on Sonnet 5 (phase 5)"` with body: what replaced what (2 calls + regex JSON → 1 structured call), FHA retry policy, social rows (3 platforms, replace-on-rerun), the new endpoint (frontend was calling a route that did not exist), shim removal, e2e evidence, test counts, merge order `#306 → #307 → #308 → #309 → this`. End with the attribution lines. Do not merge.

---

## Self-review

- **Spec coverage:** one Sonnet 5 call ✔ (Task 1); schema with mls_safe/marketing/instagram/facebook/tiktok ✔; PII sanitise ✔; top features from photo analysis ✔ (`VisionResult.features`); voice samples ✔; tone → system prompt, `_tone_to_config` kept ✔; `max_tokens` 8000 ✔; context passed once ✔ (prompt only, no `context` kwarg); FHA post-check + one retry + keep-first-with-flag ✔; `SocialContent` rows as today ✔ (plus tiktok row the frontend already renders). Extra: the missing endpoint (Task 4) — in scope because the spec's acceptance is "social page keeps working" and today it cannot.
- **Placeholders:** none.
- **Type consistency:** `ContentSocialAgent(claude=, session_factory=)` in Tasks 1, 2; results key `content_social` in Tasks 2, 5; event `content_social.completed` in Tasks 1, 2.
