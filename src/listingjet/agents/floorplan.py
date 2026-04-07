import json
import uuid

from sqlalchemy import select

from listingjet.agents.base import strip_markdown_fences
from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.dollhouse_scene import DollhouseScene
from listingjet.models.listing import Listing
from listingjet.models.vision_result import VisionResult
from listingjet.providers import get_tier2_vision_provider
from listingjet.services.metrics import record_cost

from .base import AgentContext, BaseAgent

ROOM_COLORS = {
    "living_room": "#FEF3C7",
    "kitchen": "#DBEAFE",
    "bedroom": "#E0E7FF",
    "bathroom": "#D1FAE5",
    "dining_room": "#FDE68A",
    "exterior": "#D1D5DB",
    "office": "#EDE9FE",
    "garage": "#E5E7EB",
    "pool": "#BFDBFE",
    "backyard": "#BBF7D0",
}

FLOORPLAN_EXTRACTION_PROMPT = """\
Analyze this floorplan image and extract the room layout as structured JSON.

For each room you can identify, provide:
- "label": room type (use one of: living_room, kitchen, bedroom, bathroom, dining_room, office, garage, exterior)
- "polygon": array of [x, y] coordinates defining the room boundary, normalized to 0.0-1.0 range relative to the overall floorplan dimensions
- "width_meters": estimated width in meters
- "height_meters": estimated height in meters
- "doors": array of {"wall": "north|south|east|west", "position": 0.0-1.0 along that wall}
- "windows": array of {"wall": "north|south|east|west", "position": 0.0-1.0 along that wall}

Also provide:
- "overall_width_meters": total floorplan width
- "overall_height_meters": total floorplan height

Return ONLY valid JSON with this structure:
{
  "rooms": [...],
  "overall_width_meters": number,
  "overall_height_meters": number
}
"""


class FloorplanAgent(BaseAgent):
    agent_name = "floorplan"

    def __init__(self, vision_provider=None, session_factory=None):
        self._vision_provider = vision_provider or get_tier2_vision_provider()
        self._session_factory = session_factory or AsyncSessionLocal

    def _find_floorplan_asset(self, assets: list[Asset]) -> Asset | None:
        for a in assets:
            path_lower = a.file_path.lower()
            if any(kw in path_lower for kw in ("floorplan", "floor-plan", "floor_plan", "fp_", "fp-")):
                return a
        return None

    async def execute(self, context: AgentContext) -> dict:
        async with self.session_scope(context) as (session, listing_id, tenant_id):
                listing = await session.get(Listing, listing_id)
                if not listing:
                    raise ValueError(f"Listing {listing_id} not found")

                assets_result = await session.execute(
                    select(Asset).where(Asset.listing_id == listing_id)
                )
                all_assets = assets_result.scalars().all()
                floorplan_asset = self._find_floorplan_asset(all_assets)

                if not floorplan_asset:
                    return {"room_count": 0, "skipped": True, "reason": "No floorplan asset found"}

                raw_response = await self._vision_provider.analyze_with_prompt(
                    image_url=floorplan_asset.file_path,
                    prompt=FLOORPLAN_EXTRACTION_PROMPT,
                )

                try:
                    parsed = json.loads(strip_markdown_fences(raw_response))
                    rooms = parsed.get("rooms", [])
                except (json.JSONDecodeError, AttributeError):
                    return {"room_count": 0, "skipped": True, "reason": "Failed to parse GPT-4V response"}

                vision_results = (await session.execute(
                    select(VisionResult).where(
                        VisionResult.asset_id.in_([a.id for a in all_assets]),
                        VisionResult.tier == 1,
                    ).order_by(VisionResult.quality_score.desc())
                )).scalars().all()

                best_photo_by_room: dict[str, tuple[uuid.UUID, float]] = {}
                for vr in vision_results:
                    if vr.room_label and vr.room_label not in best_photo_by_room:
                        best_photo_by_room[vr.room_label] = (vr.asset_id, vr.quality_score)

                scene_rooms = []
                for room in rooms:
                    label = room.get("label", "unknown")
                    photo_info = best_photo_by_room.get(label)
                    scene_rooms.append({
                        "label": label,
                        "polygon": room.get("polygon", []),
                        "width_meters": room.get("width_meters", 0),
                        "height_meters": room.get("height_meters", 0),
                        "doors": room.get("doors", []),
                        "windows": room.get("windows", []),
                        "color": ROOM_COLORS.get(label, "#F3F4F6"),
                        "best_photo_asset_id": str(photo_info[0]) if photo_info else None,
                        "photo_score": photo_info[1] if photo_info else None,
                    })

                scene_json = {
                    "version": 1,
                    "dimensions": {
                        "width": parsed.get("overall_width_meters", 10),
                        "height": parsed.get("overall_height_meters", 8),
                    },
                    "wall_height": 2.7,
                    "rooms": scene_rooms,
                }

                scene = DollhouseScene(
                    tenant_id=listing.tenant_id,
                    listing_id=listing_id,
                    scene_json=scene_json,
                    room_count=len(scene_rooms),
                    floorplan_asset_id=floorplan_asset.id,
                )
                session.add(scene)

                await self.emit(session, context, "floorplan.completed", {
                    "listing_id": str(listing_id),
                    "room_count": len(scene_rooms),
                })

        record_cost(self.agent_name, "qwen_vision", 1)
        return {
            "room_count": len(scene_rooms),
            "scene_id": str(scene.id),
        }
