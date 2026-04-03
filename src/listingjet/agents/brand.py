import uuid

from sqlalchemy import select

from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.brand_kit import BrandKit
from listingjet.models.listing import Listing
from listingjet.models.package_selection import PackageSelection
from listingjet.providers import get_template_provider
from listingjet.services.events import emit_event
from listingjet.services.storage import StorageService

from .base import AgentContext, BaseAgent


class BrandAgent(BaseAgent):
    agent_name = "brand"

    def __init__(self, template_provider=None, storage_service=None, session_factory=None):
        self._template_provider = template_provider or get_template_provider()
        self._storage = storage_service or StorageService()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)
        tenant_id = uuid.UUID(context.tenant_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)

                # Load hero photo
                result = await session.execute(
                    select(PackageSelection).where(
                        PackageSelection.listing_id == listing_id,
                        PackageSelection.position == 0,
                    ).limit(1)
                )
                hero = result.scalar_one_or_none()
                hero_asset_id = str(hero.asset_id) if hero else None

                # Get presigned URL for hero photo
                hero_url = None
                if hero:
                    hero_asset = await session.get(Asset, hero.asset_id)
                    if hero_asset:
                        hero_url = self._storage.presigned_url(hero_asset.file_path)

                # Load brand kit for tenant
                brand_kit = (await session.execute(
                    select(BrandKit).where(BrandKit.tenant_id == tenant_id)
                    .limit(1)
                )).scalar_one_or_none()

                # Determine template ID: tenant override or default
                template_id = "flyer-standard"
                if brand_kit and getattr(brand_kit, "canva_template_id", None):
                    template_id = brand_kit.canva_template_id

                # Build data payload with listing + brand kit fields
                data = {
                    "listing_id": str(listing_id),
                    "address": listing.address,
                    "metadata": listing.metadata_,
                    "hero_asset_id": hero_asset_id,
                    "hero_image_url": hero_url,
                    "primary_color": brand_kit.primary_color if brand_kit else "#2563EB",
                    "secondary_color": brand_kit.secondary_color if brand_kit else None,
                    "agent_name": brand_kit.agent_name if brand_kit else None,
                    "brokerage_name": brand_kit.brokerage_name if brand_kit else None,
                    "logo_url": brand_kit.logo_url if brand_kit else None,
                    "font": brand_kit.font_primary if brand_kit else None,
                }

                flyer_bytes = await self._template_provider.render(
                    template_id=template_id,
                    data=data,
                )

                s3_key = f"listings/{listing_id}/flyer.pdf"
                self._storage.upload(key=s3_key, data=flyer_bytes, content_type="application/pdf")

                await emit_event(
                    session=session,
                    event_type="brand.completed",
                    payload={"flyer_s3_key": s3_key},
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

        return {"flyer_s3_key": s3_key}
