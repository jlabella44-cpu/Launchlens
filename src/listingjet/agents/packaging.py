# src/listingjet/agents/packaging.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select

from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.learning_weight import LearningWeight
from listingjet.models.listing import Listing, ListingState
from listingjet.models.package_selection import PackageSelection
from listingjet.models.scoring_event import ScoringEvent
from listingjet.models.tenant import Tenant
from listingjet.models.vision_result import VisionResult
from listingjet.services.weight_manager import WeightManager

from .base import AgentContext, BaseAgent

MLS_MAX_PHOTOS = 25  # 1 hero + 24 supporting


class PackagingAgent(BaseAgent):
    agent_name = "packaging"

    def __init__(self, session_factory=None, weight_manager=None):
        self._session_factory = session_factory or AsyncSessionLocal
        self._wm = weight_manager or WeightManager()

    async def execute(self, context: AgentContext) -> dict:
        async with self.session_scope(context) as (session, listing_id, tenant_id):
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

                # Clear existing selections (idempotent on retry)
                await session.execute(
                    delete(PackageSelection).where(PackageSelection.listing_id == listing_id)
                )

                # Write PackageSelection + ScoringEvent rows
                for position, (score, asset_id, vr) in enumerate(top):
                    ps = PackageSelection(
                        tenant_id=tenant_id,
                        listing_id=listing_id,
                        asset_id=asset_id,
                        channel="mls",
                        position=position,
                        selected_by="ai",
                        composite_score=score,
                    )
                    session.add(ps)

                    # Log features for XGBoost training data
                    lw = weight_map.get(vr.room_label) if vr.room_label else None
                    session.add(ScoringEvent(
                        tenant_id=tenant_id,
                        listing_id=listing_id,
                        asset_id=asset_id,
                        room_label=vr.room_label,
                        features={
                            "quality_score": vr.quality_score,
                            "commercial_score": vr.commercial_score,
                            "hero_candidate": vr.hero_candidate or False,
                            "room_weight": lw.weight if lw else 1.0,
                            "tier": vr.tier,
                            "labeled_listing_count": lw.labeled_listing_count if lw else 0,
                        },
                        composite_score=score,
                        position=position,
                    ))

                # Compute average trust score
                avg_score = sum(s[0] for s in top) / len(top) if top else 0.0

                # Check if auto-approval is enabled and score meets threshold
                listing = await session.get(Listing, listing_id)
                tenant = await session.get(Tenant, tenant_id)
                auto_approved = False
                if (
                    tenant
                    and tenant.auto_approve_enabled
                    and avg_score >= tenant.auto_approve_threshold
                ):
                    listing.state = ListingState.APPROVED
                    auto_approved = True
                else:
                    listing.state = ListingState.AWAITING_REVIEW

                await self.emit(session, context, "packaging.completed", {
                    "hero_asset_id": hero_asset_id,
                    "total_selected": len(top),
                    "avg_trust_score": round(avg_score, 2),
                    "auto_approved": auto_approved,
                })

                if not auto_approved:
                    # Send review-ready notification email
                    from listingjet.services.notifications import notify_review_ready
                    await notify_review_ready(session, listing, context.tenant_id)

        return {
            "hero_asset_id": hero_asset_id,
            "total_selected": len(top),
            "avg_trust_score": round(avg_score, 2),
            "auto_approved": auto_approved,
        }
