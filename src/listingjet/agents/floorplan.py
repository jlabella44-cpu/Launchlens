import json
import logging
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
from listingjet.services.storage import get_storage

from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)

ROOM_COLORS = {
    "living_room": "#FEF3C7",
    "kitchen": "#DBEAFE",
    "bedroom": "#E0E7FF",
    "master_bedroom": "#C7D2FE",
    "bathroom": "#D1FAE5",
    "dining_room": "#FDE68A",
    "exterior": "#D1D5DB",
    "office": "#EDE9FE",
    "garage": "#E5E7EB",
    "pool": "#BFDBFE",
    "backyard": "#BBF7D0",
    "laundry": "#FCE7F3",
    "hallway": "#F3F4F6",
    "closet": "#E5E7EB",
    "foyer": "#F3F4F6",
    "mudroom": "#F3F4F6",
    "basement": "#D6D3D1",
    "attic": "#E7E5E4",
}

FLOORPLAN_VISION_LABELS = ("floorplan", "blueprint", "diagram", "site_plan")

FLOORPLAN_DOLLHOUSE_PROMPT = """\
You are analyzing a real estate floorplan to produce a 3D "dollhouse" scene.

INPUTS
- Image 1: the floorplan document.
{photo_legend}

YOUR JOB
1. Read any text on the floorplan to identify which floor this is. Look for
   labels like "Basement", "Lower Level", "First Floor", "Floor 1", "Ground
   Floor", "Second Floor", "Floor 2", "Loft", "Attic", "Garage", "Guest House",
   "ADU", etc. Use exactly what's written. If nothing is labeled, infer from
   context (a single-floor plan is "Floor 1").
2. Determine the level (integer): basements/lower-level = -1 or -2, ground/first
   floor = 1, second floor = 2, etc.
3. Determine the structure: "main_house", "detached_garage", "guest_house",
   or "adu". Default to "main_house".
4. For each room visible on the floorplan, extract layout AND appearance.
   Use the room photos (Images 2+) to ground colors, flooring, and furniture.
   Match each photo to the room on the floorplan by label.
5. For rooms that have NO photo, leave appearance fields null — do not invent.

ROOM SCHEMA — for every room return:
- "label": one of: living_room, kitchen, bedroom, master_bedroom, bathroom,
  dining_room, office, garage, laundry, hallway, closet, foyer, mudroom,
  basement, attic, exterior
- "polygon": array of [x, y] coordinates defining the room boundary, normalized
  0.0-1.0 relative to the floorplan dimensions
- "width_meters": estimated width
- "height_meters": estimated depth (length along the other axis)
- "doors": array of {{"wall": "north|south|east|west", "position": 0.0-1.0}}
- "windows": array of {{"wall": "north|south|east|west", "position": 0.0-1.0}}
- "wall_color": hex string from the matching room photo, or null
- "flooring": one of: hardwood, tile, carpet, laminate, concrete, vinyl, stone,
  or null if unknown
- "decor_tags": short descriptive tags from the photo, e.g.
  ["sage green walls", "white trim", "exposed beams"], or []
- "furniture": array of items in the room, each:
    {{"type": "sofa|sectional|bed|king_bed|queen_bed|dining_table|coffee_table|
              armchair|bookshelf|tv_stand|kitchen_island|range|fridge|toilet|
              vanity|bathtub|shower|desk|dresser|nightstand|rug",
     "x": 0.0-1.0 within the room polygon,
     "y": 0.0-1.0 within the room polygon,
     "rotation_degrees": 0-359}}
  Place furniture only when you can see it in the photo. Empty array if no
  photo for the room.

TOP LEVEL — return a single JSON object:
{{
  "floor_label": "First Floor",
  "level": 1,
  "structure": "main_house",
  "overall_width_meters": <number>,
  "overall_height_meters": <number>,
  "wall_height_meters": <number, default 2.7>,
  "rooms": [...]
}}

Return ONLY valid JSON. No markdown, no commentary.
"""


class FloorplanAgent(BaseAgent):
    agent_name = "floorplan"

    def __init__(self, vision_provider=None, session_factory=None, storage=None):
        self._vision_provider = vision_provider or get_tier2_vision_provider()
        self._session_factory = session_factory or AsyncSessionLocal
        self._storage = storage

    def _get_storage(self):
        return self._storage or get_storage()

    async def _find_floorplan_assets(
        self, session, all_assets: list[Asset]
    ) -> list[Asset]:
        """Return all assets Vision T1 tagged as floorplan-like.

        Falls back to filename heuristics for assets with no VisionResult.
        """
        asset_by_id = {a.id: a for a in all_assets}
        if not asset_by_id:
            return []

        tier1_vrs = (
            await session.execute(
                select(VisionResult).where(
                    VisionResult.asset_id.in_(asset_by_id.keys()),
                    VisionResult.tier == 1,
                )
            )
        ).scalars().all()
        tiered_ids: set[uuid.UUID] = {vr.asset_id for vr in tier1_vrs}
        found: set[uuid.UUID] = {
            vr.asset_id
            for vr in tier1_vrs
            if vr.room_label in FLOORPLAN_VISION_LABELS
        }

        for a in all_assets:
            if a.id in found or a.id in tiered_ids:
                continue
            path_lower = (a.file_path or "").lower()
            if any(
                kw in path_lower
                for kw in ("floorplan", "floor-plan", "floor_plan", "fp_", "fp-")
            ):
                found.add(a.id)

        return [asset_by_id[aid] for aid in found]

    async def _build_best_photo_map(
        self, session, all_assets: list[Asset]
    ) -> dict[str, tuple[uuid.UUID, float]]:
        vision_results = (
            await session.execute(
                select(VisionResult)
                .where(
                    VisionResult.asset_id.in_([a.id for a in all_assets]),
                    VisionResult.tier == 1,
                )
                .order_by(VisionResult.quality_score.desc())
            )
        ).scalars().all()

        best: dict[str, tuple[uuid.UUID, float]] = {}
        for vr in vision_results:
            if vr.room_label and vr.room_label not in best:
                best[vr.room_label] = (vr.asset_id, vr.quality_score)
        return best

    async def _extract_floor(
        self,
        floorplan_asset: Asset,
        all_assets: list[Asset],
        best_photo_by_room: dict[str, tuple[uuid.UUID, float]],
        storage,
    ) -> dict | None:
        floorplan_url = storage.presigned_url(floorplan_asset.file_path)

        photo_refs: list[tuple[str, str]] = []
        asset_by_id = {a.id: a for a in all_assets}
        for room_label, (asset_id, _score) in best_photo_by_room.items():
            if room_label in FLOORPLAN_VISION_LABELS:
                continue
            asset = asset_by_id.get(asset_id)
            if asset:
                photo_refs.append((room_label, storage.presigned_url(asset.file_path)))

        image_urls = [floorplan_url] + [u for _, u in photo_refs]
        photo_legend = "\n".join(
            f"Image {i + 2}: photo of the {label}"
            for i, (label, _) in enumerate(photo_refs)
        )
        prompt = FLOORPLAN_DOLLHOUSE_PROMPT.format(
            photo_legend=photo_legend or "(no room photos provided)"
        )

        try:
            raw = await self._vision_provider.analyze_with_prompt_multi(
                image_urls=image_urls, prompt=prompt
            )
        except Exception:
            logger.exception(
                "floorplan vision call failed asset=%s", floorplan_asset.id
            )
            return None

        try:
            parsed = json.loads(strip_markdown_fences(raw))
        except (json.JSONDecodeError, AttributeError):
            logger.warning("floorplan parse failed asset=%s", floorplan_asset.id)
            return None

        rooms_out = []
        for room in parsed.get("rooms", []):
            label = room.get("label", "unknown")
            photo_info = best_photo_by_room.get(label)
            rooms_out.append(
                {
                    "label": label,
                    "polygon": room.get("polygon", []),
                    "width_meters": room.get("width_meters", 0),
                    "height_meters": room.get("height_meters", 0),
                    "doors": room.get("doors", []),
                    "windows": room.get("windows", []),
                    "wall_color": room.get("wall_color"),
                    "flooring": room.get("flooring"),
                    "decor_tags": room.get("decor_tags", []),
                    "furniture": room.get("furniture", []),
                    "color": ROOM_COLORS.get(label, "#F3F4F6"),
                    "best_photo_asset_id": str(photo_info[0]) if photo_info else None,
                    "photo_score": photo_info[1] if photo_info else None,
                }
            )

        return {
            "floor_label": parsed.get("floor_label", "Floor 1"),
            "level": parsed.get("level", 1),
            "structure": parsed.get("structure", "main_house"),
            "dimensions": {
                "width_meters": parsed.get("overall_width_meters", 10),
                "height_meters": parsed.get("overall_height_meters", 8),
            },
            "wall_height_meters": parsed.get("wall_height_meters", 2.7),
            "source_floorplan_asset_id": str(floorplan_asset.id),
            "rooms": rooms_out,
        }

    async def execute(self, context: AgentContext) -> dict:
        floors: list[dict] = []
        scene_id: str | None = None
        total_rooms = 0
        floorplan_count = 0

        async with self.session_scope(context) as (session, listing_id, _tenant_id):
            listing = await session.get(Listing, listing_id)
            if not listing:
                raise ValueError(f"Listing {listing_id} not found")

            all_assets = (
                await session.execute(
                    select(Asset).where(Asset.listing_id == listing_id)
                )
            ).scalars().all()

            floorplan_assets = await self._find_floorplan_assets(session, all_assets)
            if not floorplan_assets:
                return {
                    "room_count": 0,
                    "skipped": True,
                    "reason": "No floorplan asset found",
                }

            best_photo_by_room = await self._build_best_photo_map(session, all_assets)
            storage = self._get_storage()

            for floorplan_asset in floorplan_assets:
                floor_data = await self._extract_floor(
                    floorplan_asset, all_assets, best_photo_by_room, storage
                )
                if floor_data:
                    floors.append(floor_data)

            if not floors:
                return {
                    "room_count": 0,
                    "skipped": True,
                    "reason": "Failed to extract any floor",
                }

            floors.sort(key=lambda f: f.get("level", 1))
            total_rooms = sum(len(f.get("rooms", [])) for f in floors)
            floorplan_count = len(floorplan_assets)

            scene_json = {
                "version": 2,
                "wall_height_meters": 2.7,
                "floors": floors,
            }

            scene = DollhouseScene(
                tenant_id=listing.tenant_id,
                listing_id=listing_id,
                scene_json=scene_json,
                room_count=total_rooms,
                floorplan_asset_id=floorplan_assets[0].id,
            )
            session.add(scene)
            await session.flush()
            scene_id = str(scene.id)

            await self.emit(
                session,
                context,
                "floorplan.completed",
                {
                    "listing_id": str(listing_id),
                    "room_count": total_rooms,
                    "floor_count": len(floors),
                },
            )

        record_cost(self.agent_name, "qwen_vision", floorplan_count)
        return {
            "room_count": total_rooms,
            "floor_count": len(floors),
            "scene_id": scene_id,
        }
