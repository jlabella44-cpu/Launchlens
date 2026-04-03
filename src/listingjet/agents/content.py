import json
import uuid

from sqlalchemy import select

from listingjet.agents.base import strip_markdown_fences
from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.brand_kit import BrandKit
from listingjet.models.listing import Listing
from listingjet.models.property_data import PropertyData
from listingjet.models.vision_result import VisionResult
from listingjet.providers import get_llm_provider
from listingjet.services.events import emit_event
from listingjet.services.fha_filter import fha_check
from listingjet.services.pii_filter import sanitize_for_prompt

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

# Tone intensity maps to system prompt framing + Claude temperature
_TONE_SYSTEM_PROMPTS = {
    "utility": (
        "You are a factual real estate copywriter. Focus strictly on facts and MLS compliance. "
        "No personality, no flair, no adjectives beyond what the photos show. Be concise."
    ),
    "balanced": (
        "You are a professional real estate copywriter. Use the provided example descriptions "
        "as a guide for voice and style, but adapt naturally for this property's unique features. "
        "Be compelling but grounded in the actual photos."
    ),
    "high_flair": (
        "You are a luxury real estate copywriter channeling this agent's signature voice. "
        "Deeply mimic their vocabulary, rhythm, and cadence from the examples below. "
        "Be creative, punchy, and bold — make this listing stand out."
    ),
}


def _tone_to_config(intensity: int) -> tuple[str, float]:
    """Map tone intensity (0-100) to system prompt key + Claude temperature."""
    if intensity <= 20:
        return "utility", 0.1
    elif intensity <= 60:
        return "balanced", 0.5
    else:
        return "high_flair", 0.8 + (intensity - 60) * 0.005  # 0.8-1.0


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
                    .limit(1)
                )).scalar_one_or_none()

                voice_section = ""
                if brand_kit and brand_kit.voice_samples:
                    voice_section = "\n\nMatch the voice and style of these example descriptions from this agent:\n"
                    for i, sample in enumerate(brand_kit.voice_samples[:3], 1):
                        voice_section += f"\nExample {i}: {sample}\n"

                # Market context from listing metadata
                meta = listing.metadata_ or {}
                market_context = meta.get("market_context", "")
                market_section = _MARKET_PROMPTS.get(market_context, "")

                # Tone intensity: 0-100 slider controls voice mirroring strength
                tone_intensity = meta.get("tone_intensity", 50)
                tone_key, temperature = _tone_to_config(int(tone_intensity))
                system_prompt = _TONE_SYSTEM_PROMPTS[tone_key]

                safe_metadata = sanitize_for_prompt(meta)
                prompt = _PROMPT_TEMPLATE.format(
                    metadata=str(safe_metadata),
                    photo_features=features_text or "modern interior",
                    voice_section=voice_section,
                    market_section=market_section,
                )

                prop_result = await session.execute(
                    select(PropertyData).where(PropertyData.listing_id == listing_id)
                )
                prop_data = prop_result.scalar_one_or_none()

                neighborhood_context = ""
                if prop_data:
                    parts = []
                    if isinstance(prop_data.walk_score, int) and prop_data.walk_score >= 70:
                        parts.append(f"Walk Score: {prop_data.walk_score}/100 (very walkable)")
                    if prop_data.lifestyle_tags:
                        parts.append(f"Neighborhood: {', '.join(prop_data.lifestyle_tags)}")
                    if prop_data.nearby_amenities:
                        top_amenities = prop_data.nearby_amenities[:3]
                        names = [a["name"] for a in top_amenities if isinstance(a, dict)]
                        if names:
                            parts.append(f"Nearby: {', '.join(names)}")
                    if prop_data.school_ratings:
                        ratings = prop_data.school_ratings
                        if isinstance(ratings, dict):
                            for level in ["elementary", "middle", "high"]:
                                school = ratings.get(level)
                                if isinstance(school, dict) and school.get("rating"):
                                    parts.append(f"{school['name']} ({school['rating']}/10)")
                                    break
                    if parts:
                        neighborhood_context = "\n\nNeighborhood context:\n" + "\n".join(f"- {p}" for p in parts)

                prompt += neighborhood_context

                raw = await self._llm_provider.complete(
                    prompt=prompt,
                    context=safe_metadata,
                    temperature=temperature,
                    system_prompt=system_prompt,
                )
                parsed = json.loads(strip_markdown_fences(raw))
                mls_safe = parsed["mls_safe"]
                marketing = parsed["marketing"]
                fha_result = fha_check({"mls_safe": mls_safe, "marketing": marketing})

                if not fha_result.passed:
                    raw = await self._llm_provider.complete(
                        prompt=prompt + _FHA_RETRY_SUFFIX,
                        context=safe_metadata,
                        temperature=max(0.1, temperature - 0.2),  # Lower temp for FHA retry
                        system_prompt=system_prompt,
                    )
                    parsed = json.loads(strip_markdown_fences(raw))
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
