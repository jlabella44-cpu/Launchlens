"""WatermarkAgent — overlays brand kit watermark on packaged listing photos.

Uses Pillow to composite a semi-transparent text watermark (brokerage name /
agent name) in the bottom-right corner of each selected photo. Output is
re-uploaded to S3 under a 'watermarked/' prefix.
"""
import io
import uuid

from sqlalchemy import select
from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.asset import Asset
from launchlens.models.brand_kit import BrandKit
from launchlens.models.listing import Listing
from launchlens.models.package_selection import PackageSelection
from launchlens.services.events import emit_event
from launchlens.services.storage import StorageService

from .base import AgentContext, BaseAgent

_WATERMARK_OPACITY = 180  # 0–255; 180 ≈ 70 % opaque
_FONT_SIZE = 28
_PADDING = 16


def _apply_watermark(image_bytes: bytes, text: str) -> bytes:
    """Composite a text watermark onto the bottom-right corner of the image."""
    from PIL import Image, ImageDraw, ImageFont  # type: ignore[import]

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", _FONT_SIZE)
    except OSError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

    x = img.width - text_w - _PADDING
    y = img.height - text_h - _PADDING

    # Semi-transparent dark background pill for legibility
    draw.rectangle(
        [x - 8, y - 6, x + text_w + 8, y + text_h + 6],
        fill=(0, 0, 0, _WATERMARK_OPACITY),
    )
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

    watermarked = Image.alpha_composite(img, overlay).convert("RGB")
    buf = io.BytesIO()
    watermarked.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


class WatermarkAgent(BaseAgent):
    agent_name = "watermark"

    def __init__(self, storage_service=None, session_factory=None):
        self._storage = storage_service or StorageService()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)
        tenant_id = uuid.UUID(context.tenant_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)
                if not listing:
                    raise ValueError(f"Listing {listing_id} not found")

                brand_kit = (await session.execute(
                    select(BrandKit).where(BrandKit.tenant_id == tenant_id)
                )).scalar_one_or_none()

                watermark_text = (
                    (brand_kit.brokerage_name or brand_kit.agent_name or "LaunchLens")
                    if brand_kit
                    else "LaunchLens"
                )

                # Get the packaged photos
                rows = (await session.execute(
                    select(PackageSelection, Asset)
                    .join(Asset, PackageSelection.asset_id == Asset.id)
                    .where(PackageSelection.listing_id == listing_id)
                    .order_by(PackageSelection.position)
                )).all()

                watermarked_keys: list[str] = []
                for pkg, asset in rows:
                    try:
                        img_bytes = self._storage.download(asset.file_path)
                        wm_bytes = _apply_watermark(img_bytes, watermark_text)
                        wm_key = f"listings/{listing_id}/watermarked/{asset.id}.jpg"
                        self._storage.upload(wm_key, wm_bytes, "image/jpeg")
                        watermarked_keys.append(wm_key)
                    except Exception:
                        # Non-blocking: skip photos that fail to process
                        pass

                await emit_event(
                    session=session,
                    event_type="watermark.completed",
                    payload={"watermarked_count": len(watermarked_keys), "keys": watermarked_keys},
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

        return {"watermarked_count": len(watermarked_keys)}


@activity.defn
async def run_watermark(listing_id: str, tenant_id: str) -> dict:
    agent = WatermarkAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
