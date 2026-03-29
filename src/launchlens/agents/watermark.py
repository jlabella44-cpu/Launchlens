import io
import uuid

from sqlalchemy import select

from launchlens.database import AsyncSessionLocal
from launchlens.models.asset import Asset
from launchlens.models.brand_kit import BrandKit
from launchlens.models.listing import Listing
from launchlens.models.package_selection import PackageSelection
from launchlens.models.tenant import Tenant
from launchlens.services.events import emit_event
from launchlens.services.plan_limits import get_limits
from launchlens.services.storage import StorageService

from .base import AgentContext, BaseAgent


class WatermarkAgent(BaseAgent):
    agent_name = "watermark"

    def __init__(self, storage_service=None, session_factory=None):
        self._storage = storage_service or StorageService()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)
        tenant_id = uuid.UUID(context.tenant_id)
        watermarked_count = 0

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)
                if listing is None:
                    raise ValueError(f"Listing {listing_id} not found")

                # Determine watermark mode from tenant plan
                tenant = await session.get(Tenant, tenant_id)
                plan = tenant.plan if tenant else "free"
                limits = get_limits(plan)
                watermark_mode = limits.get("watermark", "launchlens")

                # White-label (Active Agent+): skip watermarking entirely
                if watermark_mode == "none":
                    return {"watermarked_count": 0, "listing_id": str(listing_id), "mode": "white_label"}

                # Load brand kit for custom watermarks (Lite tier)
                watermark_text = "LaunchLens"
                if watermark_mode == "custom":
                    brand_kit = (await session.execute(
                        select(BrandKit).where(BrandKit.tenant_id == tenant_id)
                    )).scalar_one_or_none()
                    if brand_kit:
                        parts = []
                        if brand_kit.brokerage_name:
                            parts.append(brand_kit.brokerage_name)
                        if brand_kit.agent_name:
                            parts.append(brand_kit.agent_name)
                        if parts:
                            watermark_text = " | ".join(parts)

                result = await session.execute(
                    select(PackageSelection, Asset)
                    .join(Asset, PackageSelection.asset_id == Asset.id)
                    .where(PackageSelection.listing_id == listing_id)
                    .order_by(PackageSelection.position)
                )
                rows = result.all()

                for ps, asset in rows:
                    image_bytes = self._storage.download(asset.file_path)
                    watermarked_bytes = self._apply_watermark(image_bytes, text=watermark_text)
                    filename = asset.file_path.rsplit("/", 1)[-1]
                    upload_key = f"listings/{listing_id}/watermarked/{filename}"
                    self._storage.upload(upload_key, watermarked_bytes, "image/jpeg")
                    watermarked_count += 1

                await emit_event(
                    session=session,
                    event_type="watermark.completed",
                    payload={
                        "watermarked_count": watermarked_count,
                        "listing_id": str(listing_id),
                    },
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

        return {"watermarked_count": watermarked_count, "listing_id": str(listing_id)}

    def _apply_watermark(self, image_bytes: bytes, text: str = "LaunchLens") -> bytes:
        try:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            try:
                font = ImageFont.truetype("arial.ttf", size=max(20, img.width // 20))
            except (OSError, IOError):
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            margin = 10
            x = img.width - text_width - margin
            y = img.height - text_height - margin

            draw.text((x, y), text, fill=(255, 255, 255, 128), font=font)

            composited = Image.alpha_composite(img, overlay).convert("RGB")

            buf = io.BytesIO()
            composited.save(buf, format="JPEG", quality=90)
            return buf.getvalue()
        except Exception:
            return image_bytes
