import json
import uuid

from sqlalchemy import select
from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.asset import Asset
from launchlens.models.listing import Listing
from launchlens.models.package_selection import PackageSelection
from launchlens.models.social_content import SocialContent
from launchlens.models.vision_result import VisionResult
from launchlens.providers import get_llm_provider
from launchlens.services.events import emit_event
from launchlens.services.fha_filter import fha_check
from launchlens.services.pii_filter import sanitize_for_prompt

from .base import AgentContext, BaseAgent

_PROMPT_TEMPLATE = """\
Generate social media captions for a real estate listing.
Do NOT use Fair Housing Act prohibited language (no "perfect for families",
"safe neighborhood", "great schools", "family friendly", etc.).

Property: {address}
Details: {beds} beds, {baths} baths, {sqft} sqft, ${price:,}
Hero photo: {hero_label} (quality score: {hero_quality})
Listing description summary: {description_summary}

Return ONLY a JSON object with this exact structure:
{{
  "instagram": {{
    "caption": "...(max 2200 chars, lifestyle tone, emoji-friendly)...",
    "hashtags": ["#justlisted", "...(20-30 hashtags)..."],
    "cta": "Link in bio for details"
  }},
  "facebook": {{
    "caption": "...(max 500 chars, conversational tone, no hashtag blocks)...",
    "cta": "Schedule a showing today"
  }}
}}"""

_FHA_RETRY_SUFFIX = (
    "\n\nIMPORTANT: The previous attempt contained language that may violate the Fair Housing Act. "
    "Rewrite without referencing families, schools, neighborhood safety, or religion."
)


class SocialContentAgent(BaseAgent):
    agent_name = "social_content"

    def __init__(self, llm_provider=None, session_factory=None):
        self._llm_provider = llm_provider or get_llm_provider()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)

                # Get hero photo's VisionResult via PackageSelection (position=0) -> Asset -> VisionResult
                result = await session.execute(
                    select(VisionResult)
                    .join(Asset, VisionResult.asset_id == Asset.id)
                    .join(PackageSelection, PackageSelection.asset_id == Asset.id)
                    .where(
                        PackageSelection.listing_id == listing_id,
                        PackageSelection.position == 0,
                    )
                    .limit(1)
                )
                hero_vr = result.scalars().first()

                hero_label = hero_vr.room_label if hero_vr else "exterior"
                hero_quality = hero_vr.quality_score if hero_vr else 70

                metadata = sanitize_for_prompt(listing.metadata_ or {})
                address_dict = listing.address or {}
                address_str = f"{address_dict.get('street', '')}, {address_dict.get('city', '')}, {address_dict.get('state', '')}"

                prompt = _PROMPT_TEMPLATE.format(
                    address=address_str,
                    beds=metadata.get("beds", 0),
                    baths=metadata.get("baths", 0),
                    sqft=metadata.get("sqft", 0),
                    price=metadata.get("price", 0),
                    hero_label=hero_label,
                    hero_quality=hero_quality,
                    description_summary=metadata.get("description", "Modern property with great features"),
                )

                raw = await self._llm_provider.complete(prompt=prompt, context=metadata)
                data = json.loads(raw)

                # FHA check all captions
                fha_texts = {
                    "ig_caption": data["instagram"]["caption"],
                    "ig_cta": data["instagram"]["cta"],
                    "fb_caption": data["facebook"]["caption"],
                    "fb_cta": data["facebook"]["cta"],
                }
                fha_result = fha_check(fha_texts)

                if not fha_result.passed:
                    raw = await self._llm_provider.complete(
                        prompt=prompt + _FHA_RETRY_SUFFIX, context=metadata
                    )
                    data = json.loads(raw)
                    fha_texts = {
                        "ig_caption": data["instagram"]["caption"],
                        "ig_cta": data["instagram"]["cta"],
                        "fb_caption": data["facebook"]["caption"],
                        "fb_cta": data["facebook"]["cta"],
                    }
                    fha_result = fha_check(fha_texts)

                # Store one SocialContent row per platform
                ig = data["instagram"]
                session.add(SocialContent(
                    listing_id=listing_id,
                    tenant_id=listing.tenant_id,
                    platform="instagram",
                    caption=ig["caption"],
                    hashtags=ig.get("hashtags"),
                    cta=ig.get("cta"),
                ))

                fb = data["facebook"]
                session.add(SocialContent(
                    listing_id=listing_id,
                    tenant_id=listing.tenant_id,
                    platform="facebook",
                    caption=fb["caption"],
                    hashtags=None,
                    cta=fb.get("cta"),
                ))

                await emit_event(
                    session=session,
                    event_type="social_content.completed",
                    payload={"platforms": ["instagram", "facebook"], "fha_passed": fha_result.passed},
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

        return {"platforms": ["instagram", "facebook"], "fha_passed": fha_result.passed}


@activity.defn
async def run_social_content(listing_id: str, tenant_id: str) -> dict:
    agent = SocialContentAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
