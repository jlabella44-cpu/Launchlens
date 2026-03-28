import uuid

from sqlalchemy import select
from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.listing import Listing
from launchlens.models.package_selection import PackageSelection
from launchlens.providers import get_template_provider
from launchlens.services.events import emit_event
from launchlens.services.storage import StorageService

from .base import AgentContext, BaseAgent


class BrandAgent(BaseAgent):
    agent_name = "brand"

    def __init__(self, template_provider=None, storage_service=None, session_factory=None):
        self._template_provider = template_provider or get_template_provider()
        self._storage = storage_service or StorageService()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)

                result = await session.execute(
                    select(PackageSelection).where(
                        PackageSelection.listing_id == listing_id,
                        PackageSelection.position == 0,
                    )
                )
                hero = result.scalar_one_or_none()
                hero_asset_id = str(hero.asset_id) if hero else None

                flyer_bytes = await self._template_provider.render(
                    template_id="flyer-standard",
                    data={
                        "listing_id": str(listing_id),
                        "address": listing.address,
                        "metadata": listing.metadata_,
                        "hero_asset_id": hero_asset_id,
                    },
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


@activity.defn
async def run_brand(listing_id: str, tenant_id: str) -> dict:
    agent = BrandAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.instrumented_execute(ctx)
