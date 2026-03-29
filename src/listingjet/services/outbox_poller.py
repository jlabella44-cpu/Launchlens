# src/listingjet/services/outbox_poller.py
"""
Outbox Poller — background task for the Outbox Pattern.

Runs every POLL_INTERVAL seconds. Fetches undelivered Outbox rows,
delivers them via webhook (if tenant has webhook_url configured),
then marks delivered.

Wired into FastAPI lifespan in main.py.
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.outbox import Outbox
from listingjet.models.tenant import Tenant
from listingjet.services.webhook_delivery import deliver_webhook

logger = logging.getLogger(__name__)

POLL_INTERVAL = 5  # seconds
BATCH_SIZE = 100


class OutboxPoller:
    def __init__(self, session_factory, poll_interval: int = POLL_INTERVAL):
        self._session_factory = session_factory
        self._poll_interval = poll_interval
        self._running = False
        self._webhook_cache: dict[str, tuple[str | None, float]] = {}  # key → (url, timestamp)
        self._cache_ttl = 300  # 5 minutes

    async def _get_webhook_url(self, session: AsyncSession, tenant_id) -> str | None:
        """Look up tenant webhook URL, with TTL-based cache (5 min)."""
        import time
        key = str(tenant_id)
        now = time.time()
        if key in self._webhook_cache:
            url, cached_at = self._webhook_cache[key]
            if now - cached_at < self._cache_ttl:
                return url
        tenant = await session.get(Tenant, tenant_id)
        url = tenant.webhook_url if tenant else None
        self._webhook_cache[key] = (url, now)
        return url

    async def _process_batch(self, session: AsyncSession) -> int:
        """Fetch undelivered rows, deliver, mark done. Returns count processed."""
        try:
            result = await session.execute(
                select(Outbox)
                .where(Outbox.delivered_at.is_(None))
                .limit(BATCH_SIZE)
                .with_for_update(skip_locked=True)
            )
        except Exception:
            # FOR UPDATE SKIP LOCKED may fail inside a savepoint (e.g. tests);
            # fall back to a plain SELECT.
            result = await session.execute(
                select(Outbox)
                .where(Outbox.delivered_at.is_(None))
                .limit(BATCH_SIZE)
            )
        rows = result.scalars().all()
        now = datetime.now(timezone.utc)

        for row in rows:
            # Attempt webhook delivery if tenant has a URL configured
            webhook_url = await self._get_webhook_url(session, row.tenant_id)
            if webhook_url:
                await deliver_webhook(
                    url=webhook_url,
                    event_type=row.event_type,
                    payload=row.payload,
                    tenant_id=str(row.tenant_id),
                    listing_id=str(row.listing_id) if row.listing_id else None,
                )

            logger.info(
                "outbox.deliver event_type=%s tenant_id=%s webhook=%s",
                row.event_type,
                row.tenant_id,
                bool(webhook_url),
            )
            row.delivered_at = now

        if rows:
            await session.flush()
        return len(rows)

    async def run(self):
        """Long-running poll loop. Call from FastAPI lifespan."""
        self._running = True
        while self._running:
            try:
                async with self._session_factory() as session:
                    async with session.begin():
                        await self._process_batch(session)
            except Exception:
                logger.exception("outbox_poller: error during batch")
            await asyncio.sleep(self._poll_interval)

    def stop(self):
        self._running = False
        self._webhook_cache.clear()
