"""Image editing API — object removal, enhancement, and compliance auto-fix."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user, get_db
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing
from listingjet.models.user import User
from listingjet.providers import get_image_edit_provider
from listingjet.services.endpoint_rate_limit import rate_limit
from listingjet.services.storage import get_storage

logger = logging.getLogger(__name__)

router = APIRouter()


class RemoveObjectRequest(BaseModel):
    asset_id: uuid.UUID
    object_description: str = Field(
        ...,
        max_length=200,
        description="What to remove: 'yard sign', 'person in doorway', 'branding watermark', etc.",
    )


class EnhanceRequest(BaseModel):
    asset_id: uuid.UUID
    enhancement: str = Field(
        ...,
        description="Enhancement type: brighten, fix_lighting, improve_quality, declutter",
    )


class ImageEditResponse(BaseModel):
    original_asset_id: str
    edited_asset_id: str
    s3_key: str
    edit_type: str


async def _get_asset(
    listing_id: uuid.UUID,
    asset_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> tuple[Listing, Asset]:
    listing = (await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    asset = (await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.listing_id == listing_id)
    )).scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    return listing, asset


@router.post("/{listing_id}/assets/remove-object", response_model=ImageEditResponse)
async def remove_object(
    listing_id: uuid.UUID,
    body: RemoveObjectRequest,
    _rl=Depends(rate_limit(10, 60)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove an object from a listing photo (yard sign, person, watermark, etc.).

    Creates a new edited asset alongside the original.
    """
    listing, asset = await _get_asset(listing_id, body.asset_id, current_user.tenant_id, db)

    storage = get_storage()
    source_url = storage.presigned_url(asset.file_path, expires_in=300)

    provider = get_image_edit_provider()
    edited_bytes = await provider.remove_object(source_url, body.object_description)

    # Upload edited image
    s3_key = f"listings/{listing_id}/edited/{uuid.uuid4()}.jpg"
    storage.upload(s3_key, edited_bytes, content_type="image/jpeg")

    # Create new asset record
    edited_asset = Asset(
        tenant_id=current_user.tenant_id,
        listing_id=listing_id,
        file_path=s3_key,
        file_hash=f"edited-{asset.file_hash[:16]}",
        state="edited",
    )
    db.add(edited_asset)
    await db.commit()
    await db.refresh(edited_asset)

    logger.info(
        "image_edit.remove_object listing=%s asset=%s object=%s",
        listing_id, body.asset_id, body.object_description,
    )

    return ImageEditResponse(
        original_asset_id=str(body.asset_id),
        edited_asset_id=str(edited_asset.id),
        s3_key=s3_key,
        edit_type=f"remove:{body.object_description}",
    )


@router.post("/{listing_id}/assets/enhance", response_model=ImageEditResponse)
async def enhance_photo(
    listing_id: uuid.UUID,
    body: EnhanceRequest,
    _rl=Depends(rate_limit(10, 60)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enhance a listing photo (brighten, fix lighting, improve quality, declutter).

    Creates a new enhanced asset alongside the original.
    """
    valid_enhancements = {"brighten", "fix_lighting", "improve_quality", "declutter"}
    if body.enhancement not in valid_enhancements:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid enhancement. Choose from: {', '.join(sorted(valid_enhancements))}",
        )

    listing, asset = await _get_asset(listing_id, body.asset_id, current_user.tenant_id, db)

    storage = get_storage()
    source_url = storage.presigned_url(asset.file_path, expires_in=300)

    provider = get_image_edit_provider()
    edited_bytes = await provider.enhance(source_url, body.enhancement)

    s3_key = f"listings/{listing_id}/enhanced/{uuid.uuid4()}.jpg"
    storage.upload(s3_key, edited_bytes, content_type="image/jpeg")

    edited_asset = Asset(
        tenant_id=current_user.tenant_id,
        listing_id=listing_id,
        file_path=s3_key,
        file_hash=f"enhanced-{asset.file_hash[:16]}",
        state="enhanced",
    )
    db.add(edited_asset)
    await db.commit()
    await db.refresh(edited_asset)

    logger.info(
        "image_edit.enhance listing=%s asset=%s type=%s",
        listing_id, body.asset_id, body.enhancement,
    )

    return ImageEditResponse(
        original_asset_id=str(body.asset_id),
        edited_asset_id=str(edited_asset.id),
        s3_key=s3_key,
        edit_type=f"enhance:{body.enhancement}",
    )


@router.post("/{listing_id}/assets/auto-fix-compliance")
async def auto_fix_compliance(
    listing_id: uuid.UUID,
    _rl=Depends(rate_limit(3, 60)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Auto-fix compliance issues detected by the photo compliance agent.

    Removes yard signs, people, branding, and text overlays from flagged photos.
    Returns a list of edited assets created.
    """
    from listingjet.agents.base import AgentContext
    from listingjet.agents.photo_compliance import PhotoComplianceAgent

    listing = (await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == current_user.tenant_id)
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Run compliance check first
    compliance_agent = PhotoComplianceAgent()
    ctx = AgentContext(listing_id=str(listing_id), tenant_id=str(current_user.tenant_id))
    report = await compliance_agent.execute(ctx)

    if report.get("all_compliant", True):
        return {"fixed_count": 0, "message": "All photos are already compliant", "edits": []}

    # Auto-fix each flagged photo
    provider = get_image_edit_provider()
    storage = get_storage()
    edits = []

    for flagged in report.get("flagged_photos", []):
        asset_id = flagged["asset_id"]
        asset = await db.get(Asset, uuid.UUID(asset_id))
        if not asset:
            continue

        # Build removal description from detected issues
        issues = []
        if flagged.get("signage"):
            issues.append("real estate yard sign")
        if flagged.get("people"):
            issues.append("person/people")
        if flagged.get("branding"):
            issues.append("company branding/watermark")
        if flagged.get("text_overlay"):
            issues.append("text overlay")

        if not issues:
            continue

        description = " and ".join(issues)

        try:
            source_url = storage.presigned_url(asset.file_path, expires_in=300)
            edited_bytes = await provider.remove_object(source_url, description)

            s3_key = f"listings/{listing_id}/compliance-fixed/{uuid.uuid4()}.jpg"
            storage.upload(s3_key, edited_bytes, content_type="image/jpeg")

            edited_asset = Asset(
                tenant_id=current_user.tenant_id,
                listing_id=listing_id,
                file_path=s3_key,
                file_hash=f"fixed-{asset.file_hash[:16]}",
                state="compliance_fixed",
            )
            db.add(edited_asset)

            edits.append({
                "original_asset_id": asset_id,
                "edited_asset_id": str(edited_asset.id),
                "issues_fixed": description,
                "s3_key": s3_key,
            })

            logger.info("auto_fix_compliance asset=%s issues=%s", asset_id, description)
        except Exception:
            logger.warning("auto_fix_compliance.failed asset=%s", asset_id, exc_info=True)

    if edits:
        await db.commit()

    return {"fixed_count": len(edits), "edits": edits}
