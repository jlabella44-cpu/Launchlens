"""
Data retention and cleanup service.

Policies:
  - Outbox rows: delete delivered rows > 30 days old
  - S3 export bundles: delete after 90 days
  - Events: retain forever (audit trail)
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.health_score_history import HealthScoreHistory
from listingjet.models.listing import Listing
from listingjet.models.outbox import Outbox

logger = logging.getLogger(__name__)

OUTBOX_RETENTION_DAYS = 30
EXPORT_RETENTION_DAYS = 90
HEALTH_HISTORY_RETENTION_DAYS = 90


async def cleanup_delivered_outbox(session: AsyncSession) -> int:
    """Delete outbox rows that were delivered more than OUTBOX_RETENTION_DAYS ago."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=OUTBOX_RETENTION_DAYS)
    result = await session.execute(
        delete(Outbox).where(
            Outbox.delivered_at.isnot(None),
            Outbox.delivered_at < cutoff,
        )
    )
    count = result.rowcount
    if count:
        logger.info("data_retention.outbox_cleanup deleted=%d cutoff=%s", count, cutoff.isoformat())
    return count


async def cleanup_expired_exports(session: AsyncSession, storage=None) -> dict:
    """
    Clear S3 export bundle paths for listings delivered more than EXPORT_RETENTION_DAYS ago.
    Optionally deletes the S3 objects if a StorageService is provided.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=EXPORT_RETENTION_DAYS)

    result = await session.execute(
        select(Listing).where(
            Listing.created_at < cutoff,
            (Listing.mls_bundle_path.isnot(None)) | (Listing.marketing_bundle_path.isnot(None)),
        )
    )
    listings = result.scalars().all()

    s3_deleted = 0
    for listing in listings:
        paths = [listing.mls_bundle_path, listing.marketing_bundle_path]
        for path in paths:
            if path and storage:
                try:
                    storage.delete(path)
                    s3_deleted += 1
                except Exception:
                    logger.warning("data_retention.s3_delete_failed path=%s", path)
        listing.mls_bundle_path = None
        listing.marketing_bundle_path = None

    if listings:
        logger.info(
            "data_retention.export_cleanup listings=%d s3_deleted=%d cutoff=%s",
            len(listings), s3_deleted, cutoff.isoformat(),
        )

    return {"listings_cleaned": len(listings), "s3_deleted": s3_deleted}


async def cleanup_old_health_history(session: AsyncSession) -> int:
    """Delete health score history rows older than HEALTH_HISTORY_RETENTION_DAYS."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=HEALTH_HISTORY_RETENTION_DAYS)
    result = await session.execute(
        delete(HealthScoreHistory).where(HealthScoreHistory.calculated_at < cutoff)
    )
    count = result.rowcount
    if count:
        logger.info("data_retention.health_history_cleanup deleted=%d cutoff=%s", count, cutoff.isoformat())
    return count


async def run_all_retention(session: AsyncSession, storage=None) -> dict:
    """Run all retention policies. Call from a scheduled task or management command."""
    outbox_deleted = await cleanup_delivered_outbox(session)
    export_result = await cleanup_expired_exports(session, storage=storage)
    health_deleted = await cleanup_old_health_history(session)
    return {
        "outbox_deleted": outbox_deleted,
        **export_result,
        "health_history_deleted": health_deleted,
    }
