"""ChapterAgent — analyzes video keyframes via GPT-4V to generate chapter markers."""

import json
import uuid

from sqlalchemy import select

from launchlens.database import AsyncSessionLocal
from launchlens.models.listing import Listing
from launchlens.models.video_asset import VideoAsset
from launchlens.providers import get_vision_provider
from launchlens.services.events import emit_event
from launchlens.services.metrics import record_cost

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

    def __init__(self, vision_provider=None, session_factory=None):
        self._vision_provider = vision_provider or get_vision_provider()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
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
                    parsed = json.loads(raw_response)
                    chapters = parsed.get("chapters", [])
                except (json.JSONDecodeError, AttributeError):
                    chapters = []

                video.chapters = chapters

                await emit_event(
                    session=session,
                    event_type="chapter.completed",
                    payload={
                        "listing_id": str(listing_id),
                        "video_asset_id": str(video.id),
                        "chapter_count": len(chapters),
                    },
                    tenant_id=str(context.tenant_id),
                    listing_id=str(listing_id),
                )

        record_cost(self.agent_name, "openai_gpt4v", 1)
        return {"chapter_count": len(chapters), "video_asset_id": str(video.id)}
