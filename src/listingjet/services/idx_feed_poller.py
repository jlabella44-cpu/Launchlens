"""
IDX Feed Poller — background task that polls RESO/IDX feeds for listing updates.

Same pattern as OutboxPoller: runs in FastAPI lifespan, polls on interval.
Writes PerformanceEvent records for health score recalculation.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.idx_feed_config import IdxFeedConfig
from listingjet.models.listing import Listing
from listingjet.models.performance_event import PerformanceEvent
from listingjet.services.reso_adapter import RESOAdapter

logger = logging.getLogger(__name__)

POLL_INTERVAL = 300  # 5 minutes between poll cycles
BATCH_SIZE = 50


class IdxFeedPoller:
    def __init__(self, session_factory, poll_interval: int = POLL_INTERVAL):
        self._session_factory = session_factory
        self._poll_interval = poll_interval
        self._running = False

    async def _poll_feed(self, session: AsyncSession, config: IdxFeedConfig) -> int:
        """Poll a single IDX feed and write performance events. Returns count of updates."""
        try:
            adapter = RESOAdapter(
                base_url=config.base_url,
                api_key=config.api_key_encrypted,  # TODO: decrypt in production
            )

            # Get listings for this tenant that are in delivered state
            listings_result = await session.execute(
                select(Listing).where(
                    Listing.tenant_id == config.tenant_id,
                    Listing.state == "delivered",
                )
            )
            listings = listings_result.scalars().all()

            if not listings:
                return 0

            updates = 0
            for listing in listings:
                # Try to find this listing in the IDX feed by address
                address = listing.address or {}
                street = address.get("street", "")
                if not street:
                    continue

                try:
                    properties = await adapter.list_properties(
                        filters={"$filter": f"StreetAddress eq '{street}'"}
                    )
                except Exception:
                    logger.warning(
                        "idx_poll.query_failed feed=%s listing=%s",
                        config.name, listing.id,
                    )
                    continue

                if not properties:
                    continue

                prop = properties[0]  # Best match
                now = datetime.now(timezone.utc)

                # Record status
                mls_status = prop.get("StandardStatus", "")
                status_val = {"Active": 1.0, "Pending": 2.0, "Closed": 3.0}.get(mls_status, 0.0)
                if status_val:
                    session.add(PerformanceEvent(
                        tenant_id=config.tenant_id,
                        listing_id=listing.id,
                        signal_type="idx.status_change",
                        value=status_val,
                        source=config.name,
                        recorded_at=now,
                    ))

                # Record days on market
                dom = prop.get("DaysOnMarket")
                if dom is not None:
                    session.add(PerformanceEvent(
                        tenant_id=config.tenant_id,
                        listing_id=listing.id,
                        signal_type="idx.dom_update",
                        value=float(dom),
                        source=config.name,
                        recorded_at=now,
                    ))

                # Record photo count
                photo_count = prop.get("PhotosCount") or prop.get("MediaCount")
                if photo_count is not None:
                    session.add(PerformanceEvent(
                        tenant_id=config.tenant_id,
                        listing_id=listing.id,
                        signal_type="idx.photo_count",
                        value=float(photo_count),
                        source=config.name,
                        recorded_at=now,
                    ))

                # Record price changes
                current_price = prop.get("ListPrice")
                if current_price is not None:
                    # Check if price differs from last recorded price
                    last_price_result = await session.execute(
                        select(PerformanceEvent)
                        .where(
                            PerformanceEvent.listing_id == listing.id,
                            PerformanceEvent.signal_type == "idx.price_change",
                        )
                        .order_by(PerformanceEvent.recorded_at.desc())
                        .limit(1)
                    )
                    last_price = last_price_result.scalar_one_or_none()
                    if last_price is None or last_price.value != float(current_price):
                        session.add(PerformanceEvent(
                            tenant_id=config.tenant_id,
                            listing_id=listing.id,
                            signal_type="idx.price_change",
                            value=float(current_price),
                            source=config.name,
                            recorded_at=now,
                        ))

                updates += 1

            # Update last_polled_at
            config.last_polled_at = datetime.now(timezone.utc)
            await session.flush()
            return updates

        except Exception:
            logger.exception("idx_poll.feed_error feed=%s", config.name)
            config.status = "error"
            await session.flush()
            return 0

    async def _process_batch(self, session: AsyncSession) -> int:
        """Find feeds due for polling and process them."""
        now = datetime.now(timezone.utc)

        result = await session.execute(
            select(IdxFeedConfig).where(
                IdxFeedConfig.status == "active",
            ).limit(BATCH_SIZE)
        )
        configs = result.scalars().all()

        total = 0
        for config in configs:
            # Check if enough time has elapsed since last poll
            if config.last_polled_at:
                elapsed_min = (now - config.last_polled_at).total_seconds() / 60.0
                if elapsed_min < config.poll_interval_minutes:
                    continue

            updates = await self._poll_feed(session, config)
            total += updates
            logger.info(
                "idx_poll.completed feed=%s updates=%d", config.name, updates,
            )

        return total

    async def run(self):
        """Long-running poll loop. Call from FastAPI lifespan."""
        self._running = True
        while self._running:
            try:
                async with self._session_factory() as session:
                    async with session.begin():
                        await self._process_batch(session)
            except Exception:
                logger.exception("idx_feed_poller: error during batch")
            await asyncio.sleep(self._poll_interval)

    def stop(self):
        self._running = False
