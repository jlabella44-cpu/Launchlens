import json
import uuid

from sqlalchemy import select
from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.asset import Asset
from launchlens.models.brand_kit import BrandKit
from launchlens.models.listing import Listing
from launchlens.models.vision_result import VisionResult
from launchlens.providers import get_llm_provider
from launchlens.services.events import emit_event
from launchlens.services.fha_filter import fha_check
from launchlens.services.pii_filter import sanitize_for_prompt

from .base import AgentContext, BaseAgent

_PROMPT_TEMPLATE = """\
Write two real estate listing descriptions for the following property.
Be specific and factual. Do not use Fair Housing Act prohibited language.

Property details:
{metadata}

Key features identified from photos:
{photo_features}
{voice_section}{market_section}
Return ONLY a JSON object with this exact structure:
{{
  "mls_safe": "...(2-3 sentences, factual only, no agent promotion, no personality)...",
  "marketing": "...(2-3 sentences, compelling, personality allowed, but still FHA compliant)..."
}}"""

_FHA_RETRY_SUFFIX = (
    "\n\nIMPORTANT: The previous attempt contained language that may violate the Fair Housing Act. "
    "Rewrite without referencing families, schools, neighborhood safety, or religion."
)

_MARKET_PROMPTS = {
    "buyers_market": "\nMarket context: BUYER'S MARKET. Emphasize investment potential, value, and negotiation flexibility.",
    "hot_market": "\nMarket context: HOT MARKET. Create urgency. Emphasize demand, multiple offers expected, act fast.",
    "spring_refresh": "\nMarket context: SPRING REFRESH. Highlight fresh starts, curb appeal, outdoor living, natural light.",
    "investment": "\nMarket context: INVESTMENT OPPORTUNITY. Focus on ROI, rental potential, cap rate, location fundamentals.",
}


class ContentAgent(BaseAgent):
    agent_name = "content"

    def __init__(self, llm_provider=None, session_factory=None):
        self._llm_provider = llm_provider or get_llm_provider()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)
        tenant_id = uuid.UUID(context.tenant_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)

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

                # Load brand kit for voice samples
                brand_kit = (await session.execute(
                    select(BrandKit).where(BrandKit.tenant_id == tenant_id)
                )).scalar_one_or_none()

                voice_section = ""
                if brand_kit and brand_kit.voice_samples:
                    voice_section = "\n\nMatch the voice and style of these example descriptions from this agent:\n"
                    for i, sample in enumerate(brand_kit.voice_samples[:3], 1):
                        voice_section += f"\nExample {i}: {sample}\n"

                # Market context from listing metadata
                market_context = (listing.metadata_ or {}).get("market_context", "")
                market_section = _MARKET_PROMPTS.get(market_context, "")

                safe_metadata = sanitize_for_prompt(listing.metadata_ or {})
                prompt = _PROMPT_TEMPLATE.format(
                    metadata=str(safe_metadata),
                    photo_features=features_text or "modern interior",
                    voice_section=voice_section,
                    market_section=market_section,
                )

                raw = await self._llm_provider.complete(
                    prompt=prompt, context=safe_metadata
                )
                parsed = json.loads(raw)
                mls_safe = parsed["mls_safe"]
                marketing = parsed["marketing"]
                fha_result = fha_check({"mls_safe": mls_safe, "marketing": marketing})

                if not fha_result.passed:
                    raw = await self._llm_provider.complete(
                        prompt=prompt + _FHA_RETRY_SUFFIX, context=safe_metadata
                    )
                    parsed = json.loads(raw)
                    mls_safe = parsed["mls_safe"]
                    marketing = parsed["marketing"]
                    fha_result = fha_check({"mls_safe": mls_safe, "marketing": marketing})

                await emit_event(
                    session=session,
                    event_type="content.completed",
                    payload={
                        "fha_passed": fha_result.passed,
                        "mls_safe_length": len(mls_safe),
                        "marketing_length": len(marketing),
                        "has_voice_samples": bool(voice_section),
                        "market_context": market_context or None,
                    },
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

        return {"mls_safe": mls_safe, "marketing": marketing, "fha_passed": fha_result.passed}


@activity.defn
async def run_content(listing_id: str, tenant_id: str) -> dict:
    agent = ContentAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.instrumented_execute(ctx)
