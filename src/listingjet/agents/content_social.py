"""Listing copy and social captions in one Sonnet 5 call."""
import json
import logging
from typing import Literal, get_args

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

HookStyle = Literal["storyteller", "data_driven", "luxury_minimalist", "urgency", "lifestyle"]
HOOK_STYLES = get_args(HookStyle)
PLATFORMS = ["instagram", "facebook", "tiktok"]


class Hook(BaseModel):
    style: HookStyle = Field(description="one of: " + ", ".join(HOOK_STYLES))
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

            language = meta.get("language") or "en"
            if not isinstance(language, str):
                language = "en"
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
        try:
            tone_intensity = int(meta.get("tone_intensity", 50))
        except (TypeError, ValueError):
            tone_intensity = 50
        system = _TONE_SYSTEM_PROMPTS[_tone_to_config(tone_intensity)]
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
        ig_cta = copy.instagram.cta[:500] if copy.instagram.cta else copy.instagram.cta
        fb_cta = copy.facebook.cta[:500] if copy.facebook.cta else copy.facebook.cta
        async with self.session_scope(context) as (session, listing_id, tenant_id):
            await session.execute(delete(SocialContent).where(SocialContent.listing_id == listing_id))
            session.add_all([
                SocialContent(
                    listing_id=listing_id, tenant_id=tenant_id, platform="instagram",
                    caption=json.dumps([h.model_dump() for h in copy.instagram.hooks]),
                    hashtags=copy.instagram.hashtags, cta=ig_cta,
                ),
                SocialContent(
                    listing_id=listing_id, tenant_id=tenant_id, platform="facebook",
                    caption=json.dumps([h.model_dump() for h in copy.facebook.hooks]),
                    hashtags=None, cta=fb_cta,
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
