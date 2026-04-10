"""DollhouseRenderAgent — bakes a DollhouseScene v2 JSON into a PNG.

This is the "3D picture" stage of the dollhouse pipeline. It reads the most
recent DollhouseScene for a listing, renders it with matplotlib's 3D axes into
a single isometric PNG, uploads the PNG to S3, and writes the S3 key back into
scene_json["render_key"] so the API can presign it on the way out.
"""
from __future__ import annotations

import io
import logging
import math

import matplotlib

matplotlib.use("Agg")  # headless — must be set before pyplot import

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402, F401  (reserved for future 2D overlays)
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402
from sqlalchemy import select  # noqa: E402

from listingjet.database import AsyncSessionLocal  # noqa: E402
from listingjet.models.dollhouse_scene import DollhouseScene  # noqa: E402
from listingjet.models.listing import Listing  # noqa: E402
from listingjet.services.storage import get_storage  # noqa: E402

from .base import AgentContext, BaseAgent  # noqa: E402

logger = logging.getLogger(__name__)

# Approximate footprint sizes (meters) for common furniture types.
# Used when the vision model did not emit explicit dimensions.
FURNITURE_SIZE = {
    "sofa": (2.2, 0.9, 0.8),
    "sectional": (3.0, 1.8, 0.8),
    "armchair": (0.9, 0.9, 0.9),
    "coffee_table": (1.2, 0.6, 0.4),
    "dining_table": (1.8, 1.0, 0.75),
    "bookshelf": (1.2, 0.35, 1.8),
    "tv_stand": (1.6, 0.4, 0.5),
    "kitchen_island": (1.8, 0.9, 0.9),
    "range": (0.8, 0.65, 0.9),
    "fridge": (0.9, 0.7, 1.8),
    "toilet": (0.4, 0.6, 0.8),
    "vanity": (1.2, 0.55, 0.85),
    "bathtub": (1.7, 0.75, 0.55),
    "shower": (0.9, 0.9, 2.0),
    "desk": (1.4, 0.7, 0.75),
    "dresser": (1.4, 0.5, 0.9),
    "nightstand": (0.5, 0.4, 0.6),
    "rug": (2.4, 1.6, 0.02),
    "bed": (2.0, 1.6, 0.5),
    "queen_bed": (2.0, 1.6, 0.5),
    "king_bed": (2.1, 2.0, 0.5),
}

FLOORING_COLOR = {
    "hardwood": "#C08A5A",
    "tile": "#D9DADB",
    "carpet": "#D6CFC1",
    "laminate": "#CBA77E",
    "concrete": "#A7A7A7",
    "vinyl": "#C3B091",
    "stone": "#9B9794",
}

FURNITURE_COLOR = {
    "sofa": "#8C6E55",
    "sectional": "#8C6E55",
    "armchair": "#A0785E",
    "coffee_table": "#5C4033",
    "dining_table": "#5C4033",
    "bookshelf": "#6B4423",
    "tv_stand": "#2F2F2F",
    "kitchen_island": "#E0D6C3",
    "range": "#3A3A3A",
    "fridge": "#BDBDBD",
    "toilet": "#FFFFFF",
    "vanity": "#E8E2D0",
    "bathtub": "#F2F2F2",
    "shower": "#C8D9E6",
    "desk": "#5C4033",
    "dresser": "#5C4033",
    "nightstand": "#5C4033",
    "rug": "#C8A27C",
    "bed": "#D8CEB9",
    "queen_bed": "#D8CEB9",
    "king_bed": "#D8CEB9",
}

DEFAULT_WALL_COLOR = "#F1ECE2"
DEFAULT_FLOOR_COLOR = "#E6DFD0"
DEFAULT_FURNITURE_COLOR = "#9C9C9C"


def _polygon_bbox(polygon: list[list[float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return min(xs), min(ys), max(xs), max(ys)


def _box_faces(
    cx: float, cy: float, cz: float,
    w: float, d: float, h: float,
    rotation_deg: float = 0.0,
) -> list[list[tuple[float, float, float]]]:
    """Return the 6 faces of a box centered at (cx, cy, cz) with width/depth/height."""
    hw, hd, hh = w / 2, d / 2, h / 2
    corners_xy = [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]
    if rotation_deg:
        theta = math.radians(rotation_deg)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        corners_xy = [(x * cos_t - y * sin_t, x * sin_t + y * cos_t) for x, y in corners_xy]

    bottom = [(cx + x, cy + y, cz - hh) for x, y in corners_xy]
    top = [(cx + x, cy + y, cz + hh) for x, y in corners_xy]
    return [
        bottom,
        top,
        [bottom[0], bottom[1], top[1], top[0]],
        [bottom[1], bottom[2], top[2], top[1]],
        [bottom[2], bottom[3], top[3], top[2]],
        [bottom[3], bottom[0], top[0], top[3]],
    ]


def _render_scene_to_png(scene_json: dict) -> bytes:
    """Render a DollhouseScene v2 JSON to a PNG byte string via matplotlib 3D."""
    floors = scene_json.get("floors") or []
    if not floors:
        raise ValueError("scene_json has no floors to render")

    default_wall_height = float(scene_json.get("wall_height_meters", 2.7))

    # Figure overall bounds so we can set a reasonable aspect.
    all_x: list[float] = []
    all_y: list[float] = []
    z_base_by_index: list[float] = []

    running_z = 0.0
    sorted_floors = sorted(floors, key=lambda f: f.get("level", 1))
    for f in sorted_floors:
        z_base_by_index.append(running_z)
        running_z += float(f.get("wall_height_meters", default_wall_height)) + 0.25
    total_height = running_z

    for f in sorted_floors:
        width = float(f.get("dimensions", {}).get("width_meters", 10))
        depth = float(f.get("dimensions", {}).get("height_meters", 8))
        all_x.append(width)
        all_y.append(depth)

    max_width = max(all_x) if all_x else 10.0
    max_depth = max(all_y) if all_y else 8.0

    fig = plt.figure(figsize=(10, 7), dpi=140)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_proj_type("ortho")
    ax.view_init(elev=28, azim=-55)

    for floor, z_base in zip(sorted_floors, z_base_by_index):
        floor_width = float(floor.get("dimensions", {}).get("width_meters", max_width))
        floor_depth = float(floor.get("dimensions", {}).get("height_meters", max_depth))
        wall_h = float(floor.get("wall_height_meters", default_wall_height))

        for room in floor.get("rooms", []):
            polygon_norm = room.get("polygon") or []
            if len(polygon_norm) < 3:
                continue
            polygon = [
                (float(p[0]) * floor_width, float(p[1]) * floor_depth)
                for p in polygon_norm
            ]
            min_x, min_y, max_x, max_y = _polygon_bbox([[p[0], p[1]] for p in polygon])

            floor_color = FLOORING_COLOR.get(
                (room.get("flooring") or "").lower(),
                DEFAULT_FLOOR_COLOR,
            )
            wall_color = room.get("wall_color") or DEFAULT_WALL_COLOR

            # Floor slab
            slab = [[(x, y, z_base) for x, y in polygon]]
            ax.add_collection3d(
                Poly3DCollection(
                    slab,
                    facecolors=floor_color,
                    edgecolors="#6B5A43",
                    linewidths=0.4,
                    alpha=0.95,
                )
            )

            # Walls as short semi-transparent panels around the perimeter
            wall_panels: list[list[tuple[float, float, float]]] = []
            for i in range(len(polygon)):
                x1, y1 = polygon[i]
                x2, y2 = polygon[(i + 1) % len(polygon)]
                wall_panels.append([
                    (x1, y1, z_base),
                    (x2, y2, z_base),
                    (x2, y2, z_base + wall_h),
                    (x1, y1, z_base + wall_h),
                ])
            ax.add_collection3d(
                Poly3DCollection(
                    wall_panels,
                    facecolors=wall_color,
                    edgecolors="#6B5A43",
                    linewidths=0.35,
                    alpha=0.55,
                )
            )

            # Furniture as simple boxes
            for item in room.get("furniture") or []:
                ftype = str(item.get("type", "")).lower()
                fw, fd, fh = FURNITURE_SIZE.get(ftype, (0.6, 0.6, 0.6))
                fcol = FURNITURE_COLOR.get(ftype, DEFAULT_FURNITURE_COLOR)
                fx_norm = float(item.get("x", 0.5))
                fy_norm = float(item.get("y", 0.5))
                cx = min_x + fx_norm * (max_x - min_x)
                cy = min_y + fy_norm * (max_y - min_y)
                cz = z_base + fh / 2 + 0.01
                ax.add_collection3d(
                    Poly3DCollection(
                        _box_faces(
                            cx, cy, cz, fw, fd, fh,
                            rotation_deg=float(item.get("rotation_degrees", 0)),
                        ),
                        facecolors=fcol,
                        edgecolors="#2B2B2B",
                        linewidths=0.3,
                        alpha=0.95,
                    )
                )

            # Room label at center of floor slab
            label = (room.get("label") or "").replace("_", " ").title()
            if label:
                ax.text(
                    (min_x + max_x) / 2,
                    (min_y + max_y) / 2,
                    z_base + 0.02,
                    label,
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="#2B2B2B",
                    zorder=10,
                )

    ax.set_xlim(0, max_width)
    ax.set_ylim(0, max_depth)
    ax.set_zlim(0, max(total_height, default_wall_height))
    ax.set_box_aspect((max_width, max_depth, max(total_height, default_wall_height)))
    ax.set_axis_off()
    fig.patch.set_facecolor("#FAF7F0")
    ax.set_facecolor("#FAF7F0")
    fig.tight_layout(pad=0)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


class DollhouseRenderAgent(BaseAgent):
    agent_name = "dollhouse_render"

    def __init__(self, session_factory=None, storage=None, render_fn=None):
        self._session_factory = session_factory or AsyncSessionLocal
        self._storage = storage
        self._render_fn = render_fn or _render_scene_to_png

    def _get_storage(self):
        return self._storage or get_storage()

    async def execute(self, context: AgentContext) -> dict:
        render_key: str | None = None
        async with self.session_scope(context) as (session, listing_id, _tenant_id):
            listing = await session.get(Listing, listing_id)
            if not listing:
                raise ValueError(f"Listing {listing_id} not found")

            scene = (
                await session.execute(
                    select(DollhouseScene)
                    .where(DollhouseScene.listing_id == listing_id)
                    .order_by(DollhouseScene.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

            if not scene:
                return {
                    "skipped": True,
                    "reason": "No dollhouse scene to render",
                }

            try:
                png_bytes = self._render_fn(scene.scene_json)
            except Exception as exc:
                logger.exception(
                    "dollhouse render failed listing=%s", listing_id
                )
                return {"skipped": True, "reason": f"Render failed: {exc}"}

            storage = self._get_storage()
            render_key = f"listings/{listing_id}/dollhouse.png"
            storage.upload(key=render_key, data=png_bytes, content_type="image/png")

            # Reassign dict so SQLAlchemy detects the JSONB change.
            new_scene_json = dict(scene.scene_json or {})
            new_scene_json["render_key"] = render_key
            scene.scene_json = new_scene_json

            await self.emit(
                session,
                context,
                "dollhouse.rendered",
                {
                    "listing_id": str(listing_id),
                    "render_key": render_key,
                    "byte_size": len(png_bytes),
                },
            )

        return {"render_key": render_key}
