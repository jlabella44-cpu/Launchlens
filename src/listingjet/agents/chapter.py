"""ChapterAgent — analyzes video keyframes via GPT-4V to generate chapter markers."""

import json

from sqlalchemy import select

from listingjet.agents.base import strip_markdown_fences
from listingjet.database import AsyncSessionLocal
from listingjet.models.listing import Listing
from listingjet.models.video_asset import VideoAsset
from listingjet.providers import get_tier2_vision_provider
from listingjet.services.metrics import record_cost

from .base import AgentContext, BaseAgent

CHAPTER_EXTRACTION_PROMPT = """\
Analyze this real estate property tour video. Identify the key scene transitions and room changes.

For each distinct scene/room, provide:
- "time": approximate timestamp in seconds where the scene starts
- "label": room type (use: exterior, living_room, kitchen, bedroom, primary_bedroom, bathroom, primary_bathroom, dining_room, office, garage, pool, backyard, entryway, basement)
- "description": one-line description of what's shown

Return ONLY valid JSON:
{
  "chapters": [
    {"time": 0, "label": "exterior", "description": "Front entrance and curb appeal"},
    ...
  ]
}
"""


class ChapterAgent(BaseAgent):
    agent_name = "chapter"
    requires_ai_consent = True

    def __init__(self, vision_provider=None, session_factory=None):
        self._vision_provider = vision_provider or get_tier2_vision_provider()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        async with self.session_scope(context) as (session, listing_id, tenant_id):
                listing = await session.get(Listing, listing_id)
                if not listing:
                    raise ValueError(f"Listing {listing_id} not found")

                # Find the latest video for this listing (prefer professional, then ai_generated)
                video = (await session.execute(
                    select(VideoAsset)
                    .where(VideoAsset.listing_id == listing_id, VideoAsset.status == "ready")
                    .order_by(
                        # professional first, then by most recent
                        VideoAsset.video_type.desc(),
                        VideoAsset.created_at.desc(),
                    )
                    .limit(1)
                )).scalar_one_or_none()

                if not video:
                    return {"skipped": True, "reason": "No ready video found"}

                # For AI-generated videos, chapters are derived from clip order (already known)
                # For professional videos, use GPT-4V to analyze keyframes
                if video.video_type == "ai_generated" and video.chapters:
                    return {"skipped": True, "reason": "AI video already has chapters from clip metadata"}

                # Use GPT-4V to analyze the video thumbnail/keyframes
                raw_response = await self._vision_provider.analyze_with_prompt(
                    image_url=video.thumbnail_s3_key or video.s3_key,
                    prompt=CHAPTER_EXTRACTION_PROMPT,
                )

                try:
                    parsed = json.loads(strip_markdown_fences(raw_response))
                    chapters = parsed.get("chapters", [])
                except (json.JSONDecodeError, AttributeError):
                    chapters = []

                video.chapters = chapters

                await self.emit(session, context, "chapter.completed", {
                    "listing_id": str(listing_id),
                    "video_asset_id": str(video.id),
                    "chapter_count": len(chapters),
                })

        record_cost(self.agent_name, "qwen_vision", 1)
        return {"chapter_count": len(chapters), "video_asset_id": str(video.id)}
