# src/launchlens/agents/packaging.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.asset import Asset
from launchlens.models.learning_weight import LearningWeight
from launchlens.models.listing import Listing, ListingState
from launchlens.models.package_selection import PackageSelection
from launchlens.models.vision_result import VisionResult
from launchlens.services.events import emit_event
from launchlens.services.weight_manager import WeightManager

from .base import AgentContext, BaseAgent

MLS_MAX_PHOTOS = 25  # 1 hero + 24 supporting


class PackagingAgent(BaseAgent):
    agent_name = "packaging"

    def __init__(self, session_factory=None, weight_manager=None):
        self._session_factory = session_factory or AsyncSessionLocal
        self._wm = weight_manager or WeightManager()

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                # Load best VisionResult per asset (prefer Tier 2 over Tier 1)
                result = await session.execute(
                    select(VisionResult)
                    .join(Asset, VisionResult.asset_id == Asset.id)
                    .where(Asset.listing_id == listing_id)
                    .order_by(VisionResult.tier.desc(), VisionResult.quality_score.desc())
                )
                all_vrs = result.scalars().all()

                # Deduplicate: keep best tier result per asset
                seen: dict[uuid.UUID, VisionResult] = {}
                for vr in all_vrs:
                    if vr.asset_id not in seen:
                        seen[vr.asset_id] = vr

                # Load tenant learning weights
                tenant_id = uuid.UUID(context.tenant_id)
                lw_result = await session.execute(
                    select(LearningWeight).where(LearningWeight.tenant_id == tenant_id)
                )
                weight_map = {lw.room_label: lw for lw in lw_result.scalars().all()}

                # Score each asset
                now = datetime.now(timezone.utc)
                scored = []
                for asset_id, vr in seen.items():
                    room_weight = 1.0
                    lw = weight_map.get(vr.room_label) if vr.room_label else None
                    if lw:
                        room_weight = self._wm.blend(
                            context.tenant_id, vr.room_label,
                            lw.labeled_listing_count, lw.weight,
                        )
                        # Apply decay for stale weights
                        if lw.updated_at:
                            days_stale = (now - lw.updated_at).days
                            room_weight = self._wm.apply_decay(room_weight, days_stale)

                    features = {
                        "quality_score": vr.quality_score or 50,
                        "commercial_score": vr.commercial_score or 50,
                        "hero_candidate": vr.hero_candidate or False,
                        "room_weight": room_weight,
                    }
                    score = self._wm.score(features)
                    scored.append((score, asset_id, vr))

                scored.sort(key=lambda x: x[0], reverse=True)
                top = scored[:MLS_MAX_PHOTOS]

                hero_asset_id = str(top[0][1]) if top else None

                # Write PackageSelection rows
                for position, (score, asset_id, vr) in enumerate(top):
                    ps = PackageSelection(
                        tenant_id=uuid.UUID(context.tenant_id),
                        listing_id=listing_id,
                        asset_id=asset_id,
                        channel="mls",
                        position=position,
                        selected_by="ai",
                        composite_score=score,
                    )
                    session.add(ps)

                # Transition listing state
                listing = await session.get(Listing, listing_id)
                listing.state = ListingState.AWAITING_REVIEW

                await emit_event(
                    session=session,
                    event_type="packaging.completed",
                    payload={"hero_asset_id": hero_asset_id, "total_selected": len(top)},
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

                # Send review-ready notification email
                from launchlens.services.notifications import notify_review_ready
                await notify_review_ready(session, listing, context.tenant_id)

        return {"hero_asset_id": hero_asset_id, "total_selected": len(top)}


@activity.defn
async def run_packaging(listing_id: str, tenant_id: str) -> dict:
    agent = PackagingAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.instrumented_execute(ctx)
