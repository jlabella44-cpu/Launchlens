# src/listingjet/agents/packaging.py
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import delete, select

from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.learning_weight import LearningWeight
from listingjet.models.listing import Listing, ListingState
from listingjet.models.package_selection import PackageSelection
from listingjet.models.photo_outcome_correlation import PhotoOutcomeCorrelation
from listingjet.models.scoring_event import ScoringEvent
from listingjet.models.tenant import Tenant
from listingjet.models.vision_result import VisionResult
from listingjet.services.weight_manager import WeightManager

from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)

MLS_MAX_PHOTOS = 25  # 1 hero + 24 supporting
DEFAULT_ROOM_WEIGHT = 1.0  # Neutral weight when no LearningWeight data exists
MIN_QUALITY_SCORE = 25  # Skip photos below this quality threshold

# Required rooms: must include at least 1 of each if available
REQUIRED_ROOMS = ["exterior", "kitchen", "living_room", "bathroom"]

# Max slots per room type (prevents overrepresentation)
ROOM_MAX_SLOTS: dict[str, int] = {
    "exterior": 4,
    "living_room": 2,
    "kitchen": 2,
    "dining_room": 2,
    "bedroom": 3,
    "bathroom": 3,
    "office": 1,
    "backyard": 2,
    "pool": 2,
    "garage": 1,
    "basement": 1,
    "laundry": 0,  # exclude
}

# MLS position ordering — exterior first, then interior flow
MLS_POSITION_ORDER = [
    "exterior",
    "living_room",
    "kitchen",
    "dining_room",
    "bedroom",
    "bathroom",
    "office",
    "backyard",
    "pool",
    "garage",
    "basement",
]


class PackagingAgent(BaseAgent):
    agent_name = "packaging"

    def __init__(self, session_factory=None, weight_manager=None):
        self._session_factory = session_factory or AsyncSessionLocal
        self._wm = weight_manager or WeightManager()

    @staticmethod
    def _select_diverse(
        scored: list[tuple[float, uuid.UUID, VisionResult]],
    ) -> list[tuple[float, uuid.UUID, VisionResult]]:
        """Select up to MLS_MAX_PHOTOS with room diversity constraints."""
        # Filter quality floor
        candidates = [
            (s, aid, vr) for s, aid, vr in scored
            if (vr.quality_score or 50) >= MIN_QUALITY_SCORE
        ]

        # Filter excluded rooms (max_slots == 0)
        candidates = [
            (s, aid, vr) for s, aid, vr in candidates
            if ROOM_MAX_SLOTS.get(vr.room_label, 2) > 0
        ]

        selected: list[tuple[float, uuid.UUID, VisionResult]] = []
        selected_ids: set[uuid.UUID] = set()
        room_counts: dict[str, int] = defaultdict(int)

        # Phase 1: Guarantee required rooms (best photo per required room)
        for required in REQUIRED_ROOMS:
            for s, aid, vr in candidates:
                if aid in selected_ids:
                    continue
                if vr.room_label == required:
                    selected.append((s, aid, vr))
                    selected_ids.add(aid)
                    room_counts[required] += 1
                    break

        # Phase 2: Fill remaining slots by score, respecting room caps
        for s, aid, vr in candidates:
            if len(selected) >= MLS_MAX_PHOTOS:
                break
            if aid in selected_ids:
                continue
            room = vr.room_label or "_unknown"
            max_slots = ROOM_MAX_SLOTS.get(room, 2)
            if room_counts[room] >= max_slots:
                continue
            selected.append((s, aid, vr))
            selected_ids.add(aid)
            room_counts[room] += 1

        return selected

    @staticmethod
    def _reorder_mls(
        selected: list[tuple[float, uuid.UUID, VisionResult]],
    ) -> list[tuple[float, uuid.UUID, VisionResult]]:
        """Reorder selected photos to follow MLS best practice positioning."""
        priority = {room: i for i, room in enumerate(MLS_POSITION_ORDER)}
        max_priority = len(MLS_POSITION_ORDER)

        # Hero: best exterior, or best overall if no exterior
        hero = None
        rest = []
        for item in selected:
            if hero is None and item[2].room_label == "exterior":
                hero = item
            else:
                rest.append(item)

        if hero is None and selected:
            hero = selected[0]
            rest = selected[1:]

        # Sort rest by room priority, then by score within room
        rest.sort(key=lambda x: (
            priority.get(x[2].room_label or "_unknown", max_priority),
            -x[0],  # higher score first within same room
        ))

        result = []
        if hero:
            result.append(hero)
        result.extend(rest)
        return result

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

                # Phase 5: Load outcome-based boosts per room
                oc_result = await session.execute(
                    select(PhotoOutcomeCorrelation).where(
                        PhotoOutcomeCorrelation.tenant_id == tenant_id,
                        PhotoOutcomeCorrelation.dimension == "room_label",
                    )
                )
                outcome_boost_map = {
                    oc.dimension_value: (oc.outcome_boost, oc.sample_count)
                    for oc in oc_result.scalars().all()
                }

                # Score each asset
                now = datetime.now(timezone.utc)
                scored = []
                for asset_id, vr in seen.items():
                    room_weight = DEFAULT_ROOM_WEIGHT
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

                    # Phase 5: outcome boost from real sale data
                    ob = outcome_boost_map.get(vr.room_label, (1.0, 0)) if vr.room_label else (1.0, 0)

                    features = {
                        "quality_score": vr.quality_score or 50,
                        "commercial_score": vr.commercial_score or 50,
                        "hero_candidate": vr.hero_candidate or False,
                        "room_weight": room_weight,
                        "outcome_boost": ob[0],
                        "outcome_samples": ob[1],
                    }
                    score = self._wm.score(features)
                    scored.append((score, asset_id, vr))

                scored.sort(key=lambda x: x[0], reverse=True)

                # Diversity-aware selection + MLS ordering
                top = self._select_diverse(scored)
                top = self._reorder_mls(top)

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
                            "room_weight": lw.weight if lw else DEFAULT_ROOM_WEIGHT,
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
