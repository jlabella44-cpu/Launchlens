# src/launchlens/services/outbox_poller.py
"""
Outbox Poller — background task for the Outbox Pattern.

Runs every POLL_INTERVAL seconds. Fetches undelivered Outbox rows,
delivers them (logs + future: pushes to webhook/queue), marks delivered.

Wired into FastAPI lifespan in main.py.
"""
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from launchlens.models.outbox import Outbox

logger = logging.getLogger(__name__)

POLL_INTERVAL = 5  # seconds
BATCH_SIZE = 100


class OutboxPoller:
    def __init__(self, session_factory, poll_interval: int = POLL_INTERVAL):
        self._session_factory = session_factory
        self._poll_interval = poll_interval
        self._running = False

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
            logger.info(
                "outbox.deliver event_type=%s tenant_id=%s",
                row.event_type,
                row.tenant_id,
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
