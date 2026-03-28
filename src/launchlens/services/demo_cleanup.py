"""
Demo listing cleanup service.

Deletes expired demo listings and their associated assets from both
the database and S3. Designed to be called by a Temporal cron workflow
running hourly.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from launchlens.models.asset import Asset
from launchlens.models.listing import Listing, ListingState
from launchlens.services.storage import StorageService

logger = logging.getLogger(__name__)


async def cleanup_expired_demos(session: AsyncSession, storage: StorageService | None = None) -> dict:
    """
    Delete all demo listings past their demo_expires_at.

    Returns a summary dict: {"deleted_listings": int, "deleted_assets": int, "s3_cleaned": int}
    """
    now = datetime.now(timezone.utc)

    # Find expired demo listings
    result = await session.execute(
        select(Listing).where(
            Listing.is_demo.is_(True),
            Listing.demo_expires_at < now,
        )
    )
    expired = result.scalars().all()

    if not expired:
        return {"deleted_listings": 0, "deleted_assets": 0, "s3_cleaned": 0}

    listing_ids = [l.id for l in expired]
    s3_cleaned = 0

    # Clean up S3 assets if storage provided
    if storage:
        asset_result = await session.execute(
            select(Asset).where(Asset.listing_id.in_(listing_ids))
        )
        assets = asset_result.scalars().all()
        for asset in assets:
            try:
                storage.delete(asset.file_path)
                s3_cleaned += 1
            except Exception:
                logger.warning("Failed to delete S3 object: %s", asset.file_path)

    # Delete assets from DB
    asset_delete = await session.execute(
        delete(Asset).where(Asset.listing_id.in_(listing_ids))
    )
    deleted_assets = asset_delete.rowcount

    # Delete listings from DB
    listing_delete = await session.execute(
        delete(Listing).where(Listing.id.in_(listing_ids))
    )
    deleted_listings = listing_delete.rowcount

    await session.commit()

    logger.info(
        "Demo cleanup: deleted %d listings, %d assets, %d S3 objects",
        deleted_listings, deleted_assets, s3_cleaned,
    )

    return {
        "deleted_listings": deleted_listings,
        "deleted_assets": deleted_assets,
        "s3_cleaned": s3_cleaned,
    }
