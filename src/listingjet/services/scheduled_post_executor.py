"""Scheduled Post Executor — background task that publishes due posts.

Same pattern as OutboxPoller / IdxFeedPoller: runs in FastAPI lifespan.
Polls every 60s for posts where status='scheduled' and scheduled_at <= now.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.scheduled_post import ScheduledPost
from listingjet.models.social_account import SocialAccount
from listingjet.services.social_publisher import get_publisher

logger = logging.getLogger(__name__)

POLL_INTERVAL = 60  # seconds
MAX_RETRIES = 3
RETRY_DELAY_MINUTES = 5


class ScheduledPostExecutor:
    def __init__(self, session_factory, poll_interval: int = POLL_INTERVAL):
        self._session_factory = session_factory
        self._poll_interval = poll_interval
        self._running = False

    async def _process_post(self, session: AsyncSession, post: ScheduledPost) -> None:
        """Attempt to publish a single scheduled post."""
        post.status = "publishing"
        await session.flush()

        # Find the connected social account
        result = await session.execute(
            select(SocialAccount).where(
                SocialAccount.tenant_id == post.tenant_id,
                SocialAccount.platform == post.platform,
                SocialAccount.status == "connected",
            ).limit(1)
        )
        account = result.scalar_one_or_none()

        if not account:
            post.status = "failed"
            post.error_message = f"No connected {post.platform} account found"
            await session.flush()
            logger.warning(
                "scheduled_post.no_account post=%s platform=%s tenant=%s",
                post.id, post.platform, post.tenant_id,
            )
            return

        publisher = get_publisher(post.platform)
        publish_result = await publisher.publish(account, post)

        if publish_result.success:
            post.status = "published"
            post.platform_post_id = publish_result.platform_post_id
            post.platform_post_url = publish_result.platform_post_url
            post.published_at = datetime.now(timezone.utc)
            post.error_message = None
            logger.info(
                "scheduled_post.published post=%s platform=%s url=%s",
                post.id, post.platform, publish_result.platform_post_url,
            )
        else:
            post.retry_count += 1
            if post.retry_count >= MAX_RETRIES:
                post.status = "failed"
                post.error_message = publish_result.error
                logger.error(
                    "scheduled_post.failed post=%s platform=%s retries=%d error=%s",
                    post.id, post.platform, post.retry_count, publish_result.error,
                )
            else:
                # Reschedule for retry
                post.status = "scheduled"
                post.scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=RETRY_DELAY_MINUTES)
                post.error_message = publish_result.error
                logger.warning(
                    "scheduled_post.retry post=%s platform=%s attempt=%d next=%s",
                    post.id, post.platform, post.retry_count, post.scheduled_at,
                )

        await session.flush()

    async def _process_batch(self, session: AsyncSession) -> int:
        """Find and process all due scheduled posts."""
        now = datetime.now(timezone.utc)
        result = await session.execute(
            select(ScheduledPost)
            .where(
                ScheduledPost.status == "scheduled",
                ScheduledPost.scheduled_at <= now,
            )
            .limit(50)
        )
        posts = result.scalars().all()

        for post in posts:
            try:
                await self._process_post(session, post)
            except Exception:
                logger.exception("scheduled_post.executor_error post=%s", post.id)
                post.status = "failed"
                post.error_message = "Internal executor error"
                await session.flush()

        return len(posts)

    async def run(self):
        """Long-running poll loop."""
        self._running = True
        while self._running:
            try:
                async with self._session_factory() as session:
                    async with session.begin():
                        count = await self._process_batch(session)
                        if count:
                            logger.info("scheduled_post.batch_processed count=%d", count)
            except Exception:
                logger.exception("scheduled_post_executor: error during batch")
            await asyncio.sleep(self._poll_interval)

    def stop(self):
        self._running = False
