"""Start the listing pipeline: resolve enabled addons and enqueue jobs."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.addon_catalog import AddonCatalog
from listingjet.models.addon_purchase import AddonPurchase
from listingjet.models.listing import Listing
from listingjet.models.pipeline_job import PipelineJob
from listingjet.models.tenant import Tenant
from listingjet.pipeline.runner import enqueue_pipeline


async def enabled_addon_slugs(session: AsyncSession, listing_id) -> list[str]:
    """Active addon slugs purchased for a listing (AddonPurchase joined to AddonCatalog)."""
    result = await session.execute(
        select(AddonCatalog.slug)
        .join(AddonPurchase, AddonPurchase.addon_id == AddonCatalog.id)
        .where(AddonPurchase.listing_id == listing_id, AddonPurchase.status == "active")
    )
    return [row[0] for row in result.all()]


async def start_listing_pipeline(session: AsyncSession, listing: Listing, tenant: Tenant | None) -> list[PipelineJob]:
    billing_model = tenant.billing_model if tenant else "legacy"
    slugs = await enabled_addon_slugs(session, listing.id)
    return await enqueue_pipeline(session, listing, billing_model=billing_model, enabled_addons=slugs)
