"""MLS photo-compliance reporting.

The compliance flags now come from the single `PhotoAnalysisAgent` pass that
writes them onto `VisionResult.compliance`; this module only reads them back
and shapes them into the report dict that the API and the auto-fix endpoint
already expect (the shape the old standalone compliance agent returned).
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.asset import Asset
from listingjet.models.package_selection import PackageSelection
from listingjet.models.vision_result import VisionResult

# Flag key -> human label used in the reasoning / issues_summary string.
FLAG_LABELS: dict[str, str] = {
    "branding": "branding",
    "signage": "signage",
    "people": "people",
    "text_overlay": "text overlay",
}

NO_ISSUES = "No issues found"


def summarize_flags(compliance: dict | None) -> str:
    """A short human string naming the raised flags, or 'No issues found'."""
    issues = [label for key, label in FLAG_LABELS.items() if (compliance or {}).get(key)]
    return ", ".join(issues) if issues else NO_ISSUES


async def _analysis_by_asset(session: AsyncSession, asset_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict]:
    """Latest analysed compliance payload per asset id."""
    if not asset_ids:
        return {}
    rows = (await session.execute(
        select(VisionResult)
        .where(VisionResult.asset_id.in_(asset_ids), VisionResult.compliance.isnot(None))
        .order_by(VisionResult.created_at)
    )).scalars().all()
    return {vr.asset_id: vr.compliance for vr in rows}


async def compliance_report(session: AsyncSession, listing_id) -> dict:
    """Build the per-photo MLS compliance report for a listing.

    Reads the packaged photos when the listing has a package; falls back to
    every analysed asset on the listing when nothing has been packaged yet.
    Assets with no analysis are excluded — they have nothing to report on.
    """
    lid = listing_id if isinstance(listing_id, uuid.UUID) else uuid.UUID(str(listing_id))

    ordered_ids = list((await session.execute(
        select(PackageSelection.asset_id)
        .where(PackageSelection.listing_id == lid)
        .order_by(PackageSelection.position)
    )).scalars().all())

    if not ordered_ids:
        ordered_ids = list((await session.execute(
            select(Asset.id).where(Asset.listing_id == lid).order_by(Asset.created_at, Asset.id)
        )).scalars().all())

    # De-duplicate while preserving order (an asset can be packaged per channel).
    seen: set[uuid.UUID] = set()
    unique_ids = [i for i in ordered_ids if not (i in seen or seen.add(i))]

    compliance_by_asset = await _analysis_by_asset(session, unique_ids)

    decisions = []
    flagged_photos = []
    for asset_id in unique_ids:
        compliance = compliance_by_asset.get(asset_id)
        if compliance is None:
            continue
        flags = {key: bool(compliance.get(key)) for key in FLAG_LABELS}
        compliant = not any(flags.values())
        summary = summarize_flags(compliance)
        decisions.append({
            "asset_id": str(asset_id),
            "compliant": compliant,
            **flags,
            "reasoning": summary,
        })
        if not compliant:
            flagged_photos.append({
                "asset_id": str(asset_id),
                **flags,
                "issues_summary": summary,
            })

    return {
        "total_photos": len(decisions),
        "compliant_count": len(decisions) - len(flagged_photos),
        "flagged_count": len(flagged_photos),
        "all_compliant": not flagged_photos,
        "decisions": decisions,
        "flagged_photos": flagged_photos,
    }
