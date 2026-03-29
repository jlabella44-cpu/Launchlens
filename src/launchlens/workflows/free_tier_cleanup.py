"""
Temporal cron workflow for free tier asset expiry.

Schedule: runs daily via Temporal cron.
Activity: deletes S3 assets older than 30 days for free/PAYG tenants.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from temporalio import activity, workflow
from temporalio.common import RetryPolicy

logger = logging.getLogger(__name__)


@activity.defn
async def run_free_tier_cleanup() -> dict:
    from launchlens.database import AsyncSessionLocal
    from launchlens.models.asset import Asset
    from launchlens.models.listing import Listing
    from launchlens.models.tenant import Tenant
    from launchlens.services.storage import StorageService

    storage = StorageService()
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    expired_count = 0

    async with AsyncSessionLocal() as session:
        # Find free tier tenants
        free_tenants = (await session.execute(
            select(Tenant.id).where(Tenant.plan == "free")
        )).scalars().all()

        if not free_tenants:
            return {"expired_count": 0, "free_tenants": 0}

        # Find assets older than 30 days belonging to free tenants
        result = await session.execute(
            select(Asset).join(Listing, Asset.listing_id == Listing.id).where(
                Listing.tenant_id.in_(free_tenants),
                Asset.created_at < cutoff,
                Asset.state != "expired",
            )
        )
        expired_assets = result.scalars().all()

        for asset in expired_assets:
            try:
                storage.delete(asset.file_path)
            except Exception:
                pass  # S3 delete failure is non-fatal
            asset.state = "expired"
            expired_count += 1

        await session.commit()

    logger.info("free_tier_cleanup expired=%d tenants=%d", expired_count, len(free_tenants))
    return {"expired_count": expired_count, "free_tenants": len(free_tenants)}


@workflow.defn
class FreeTierCleanupWorkflow:
    """Cron workflow — Temporal schedules this daily."""

    @workflow.run
    async def run(self) -> dict:
        return await workflow.execute_activity(
            run_free_tier_cleanup,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
