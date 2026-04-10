"""
PerformanceIntelligenceAgent — links photo selections to listing outcomes.

Runs in two contexts:
  1. Post-delivery (pipeline Step 9): creates initial ListingOutcome stub
     so correlations include the listing once IDX data arrives.
  2. On IDX outcome ingestion: recomputes tenant-wide correlations when
     a listing goes to Closed.

This agent is the bridge between the IDX feed poller (external data)
and the learning/packaging system (internal scoring).
"""
import logging

from sqlalchemy import func, select

from listingjet.database import AsyncSessionLocal
from listingjet.models.listing import Listing
from listingjet.models.listing_outcome import ListingOutcome
from listingjet.models.package_selection import PackageSelection
from listingjet.models.vision_result import VisionResult
from listingjet.services.outcome_tracker import compute_correlations

from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)


class PerformanceIntelligenceAgent(BaseAgent):
    agent_name = "performance_intelligence"

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        async with self.session_scope(context) as (session, listing_id, tenant_id):
            listing = await session.get(Listing, listing_id)
            if not listing:
                return {"status": "skipped", "reason": "listing_not_found"}

            # Check if outcome already exists
            existing = await session.execute(
                select(ListingOutcome).where(ListingOutcome.listing_id == listing_id)
            )
            outcome = existing.scalar_one_or_none()

            if not outcome:
                # Create initial stub with photo package stats
                pkg_result = await session.execute(
                    select(PackageSelection).where(
                        PackageSelection.listing_id == listing_id,
                        PackageSelection.channel == "mls",
                    ).order_by(PackageSelection.position.asc())
                )
                selections = pkg_result.scalars().all()

                hero_room_label = None
                if selections:
                    hero_sel = selections[0]
                    vr_result = await session.execute(
                        select(VisionResult).where(
                            VisionResult.asset_id == hero_sel.asset_id,
                        ).limit(1)
                    )
                    hero_vr = vr_result.scalar_one_or_none()
                    if hero_vr:
                        hero_room_label = hero_vr.room_label

                outcome = ListingOutcome(
                    tenant_id=tenant_id,
                    listing_id=listing_id,
                    status="active",
                    photo_count=len(selections),
                    hero_room_label=hero_room_label,
                )
                session.add(outcome)
                logger.info(
                    "perf_intel.stub_created listing=%s photos=%d hero=%s",
                    listing_id, len(selections), hero_room_label,
                )

            # Count closed outcomes for this tenant
            closed_count = (await session.execute(
                select(func.count()).select_from(ListingOutcome).where(
                    ListingOutcome.tenant_id == tenant_id,
                    ListingOutcome.status == "closed",
                )
            )).scalar() or 0

            # Recompute correlations if we have enough closed data
            correlations_updated = 0
            if closed_count >= 3:
                correlations_updated = await compute_correlations(session, tenant_id)

            await self.emit(session, context, "performance_intelligence.completed", {
                "listing_id": str(listing_id),
                "outcome_status": outcome.status if outcome else "new",
                "closed_count": closed_count,
                "correlations_updated": correlations_updated,
            })

        return {
            "status": "completed",
            "closed_count": closed_count,
            "correlations_updated": correlations_updated,
        }
