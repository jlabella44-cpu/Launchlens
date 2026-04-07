"""
Health Score Agent — calculates composite listing health score after pipeline completion.

Runs as the final Temporal activity. Non-blocking: pipeline completes even if this fails.
Emits health.score.updated event and health.score.alert if below threshold.
"""
import logging

from sqlalchemy import select

from listingjet.database import AsyncSessionLocal
from listingjet.models.tenant import Tenant
from listingjet.services import health_score as hs

from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)

DEFAULT_ALERT_THRESHOLD = 60


class HealthScoreAgent(BaseAgent):
    agent_name = "health_score"

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        async with self.session_scope(context) as (session, listing_id, tenant_id):
            # Resolve tenant plan + custom weights
            tenant = await session.get(Tenant, tenant_id)
            plan = tenant.plan if tenant else "starter"

            score = await hs.calculate(
                session=session,
                listing_id=listing_id,
                tenant_id=tenant_id,
                plan=plan,
            )

            await self.emit(session, context, "health.score.updated", {
                "listing_id": str(listing_id),
                "overall_score": score.overall_score,
                "media_score": score.media_score,
                "content_score": score.content_score,
                "velocity_score": score.velocity_score,
                "syndication_score": score.syndication_score,
                "market_score": score.market_score,
            })

            # Check alert threshold
            threshold = DEFAULT_ALERT_THRESHOLD
            if score.overall_score < threshold:
                await self.emit(session, context, "health.score.alert", {
                    "listing_id": str(listing_id),
                    "overall_score": score.overall_score,
                    "threshold": threshold,
                })
                logger.warning(
                    "health.score.alert listing=%s score=%d threshold=%d",
                    listing_id, score.overall_score, threshold,
                )

        return {
            "overall_score": score.overall_score,
            "media_score": score.media_score,
            "content_score": score.content_score,
        }
