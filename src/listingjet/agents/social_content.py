import json
import uuid

from sqlalchemy import select

from listingjet.agents.base import strip_markdown_fences
from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing
from listingjet.models.package_selection import PackageSelection
from listingjet.models.social_content import SocialContent
from listingjet.models.vision_result import VisionResult
from listingjet.providers import get_llm_provider
from listingjet.services.events import emit_event
from listingjet.services.fha_filter import fha_check
from listingjet.services.pii_filter import sanitize_for_prompt

from .base import AgentContext, BaseAgent

_PROMPT_TEMPLATE = """\
Generate social media captions for a real estate listing.
Do NOT use Fair Housing Act prohibited language (no "perfect for families",
"safe neighborhood", "great schools", "family friendly", etc.).

Property: {address}
Details: {beds} beds, {baths} baths, {sqft} sqft, ${price:,}
Hero photo: {hero_label} (quality score: {hero_quality})
Listing description summary: {description_summary}

Generate FIVE distinct "hook" variations for each platform. Each hook should take
a different angle: storyteller (narrative), data-driven (numbers), luxury minimalist
(understated), urgency (FOMO), and lifestyle (paint the dream).

Return ONLY a JSON object with this exact structure:
{{
  "instagram": {{
    "hooks": [
      {{"style": "storyteller", "caption": "...(narrative opening, max 2200 chars)..."}},
      {{"style": "data_driven", "caption": "...(lead with numbers)..."}},
      {{"style": "luxury_minimalist", "caption": "...(understated elegance)..."}},
      {{"style": "urgency", "caption": "...(FOMO, act fast)..."}},
      {{"style": "lifestyle", "caption": "...(paint the dream)..."}}
    ],
    "hashtags": ["#justlisted", "...(20-30 hashtags)..."],
    "cta": "Link in bio for details"
  }},
  "facebook": {{
    "hooks": [
      {{"style": "storyteller", "caption": "...(max 500 chars)..."}},
      {{"style": "data_driven", "caption": "..."}},
      {{"style": "luxury_minimalist", "caption": "..."}},
      {{"style": "urgency", "caption": "..."}},
      {{"style": "lifestyle", "caption": "..."}}
    ],
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
                data = json.loads(strip_markdown_fences(raw))

                # FHA check all captions (handle both hooks and flat format)
                fha_texts = {}
                for platform in ("instagram", "facebook"):
                    hooks = data[platform].get("hooks", [])
                    if hooks:
                        for i, hook in enumerate(hooks):
                            fha_texts[f"{platform}_hook_{i}"] = hook.get("caption", "")
                    else:
                        fha_texts[f"{platform}_caption"] = data[platform].get("caption", "")
                    fha_texts[f"{platform}_cta"] = data[platform].get("cta", "")
                fha_result = fha_check(fha_texts)

                if not fha_result.passed:
                    raw = await self._llm_provider.complete(
                        prompt=prompt + _FHA_RETRY_SUFFIX, context=metadata
                    )
                    data = json.loads(strip_markdown_fences(raw))
                    fha_texts = {}
                    for platform in ("instagram", "facebook"):
                        hooks = data[platform].get("hooks", [])
                        if hooks:
                            for i, hook in enumerate(hooks):
                                fha_texts[f"{platform}_hook_{i}"] = hook.get("caption", "")
                        else:
                            fha_texts[f"{platform}_caption"] = data[platform].get("caption", "")
                        fha_texts[f"{platform}_cta"] = data[platform].get("cta", "")
                    fha_result = fha_check(fha_texts)

                # Store one SocialContent row per platform
                # Hooks are stored as JSON array in caption field
                ig = data["instagram"]
                ig_hooks = ig.get("hooks", [])
                ig_caption = ig_hooks[0]["caption"] if ig_hooks else ig.get("caption", "")
                session.add(SocialContent(
                    listing_id=listing_id,
                    tenant_id=listing.tenant_id,
                    platform="instagram",
                    caption=json.dumps(ig_hooks) if ig_hooks else ig_caption,
                    hashtags=ig.get("hashtags"),
                    cta=ig.get("cta"),
                ))

                fb = data["facebook"]
                fb_hooks = fb.get("hooks", [])
                fb_caption = fb_hooks[0]["caption"] if fb_hooks else fb.get("caption", "")
                session.add(SocialContent(
                    listing_id=listing_id,
                    tenant_id=listing.tenant_id,
                    platform="facebook",
                    caption=json.dumps(fb_hooks) if fb_hooks else fb_caption,
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
