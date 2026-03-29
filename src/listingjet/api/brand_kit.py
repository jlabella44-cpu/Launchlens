"""
Brand Kit API — CRUD for tenant branding configuration.

Endpoints:
  GET  /brand-kit             — get current tenant's brand kit (or null)
  PUT  /brand-kit             — create or update (upsert)
  POST /brand-kit/logo-upload-url — presigned S3 URL for logo upload
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.brand_kit import BrandKitResponse, BrandKitUpsertRequest
from listingjet.database import get_db
from listingjet.models.brand_kit import BrandKit
from listingjet.models.user import User
from listingjet.services.storage import StorageService

router = APIRouter()


@router.get("", response_model=BrandKitResponse | None)
async def get_brand_kit(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current tenant's brand kit, or null if not configured."""
    result = await db.execute(
        select(BrandKit).where(BrandKit.tenant_id == current_user.tenant_id).limit(1)
    )
    kit = result.scalar_one_or_none()
    return kit


@router.put("", response_model=BrandKitResponse)
async def upsert_brand_kit(
    body: BrandKitUpsertRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update the tenant's brand kit."""
    result = await db.execute(
        select(BrandKit).where(BrandKit.tenant_id == current_user.tenant_id).limit(1)
    )
    kit = result.scalar_one_or_none()

    if kit is None:
        kit = BrandKit(
            id=uuid.uuid4(),
            tenant_id=current_user.tenant_id,
        )
        db.add(kit)

    if body.logo_url is not None:
        kit.logo_url = body.logo_url
    if body.primary_color is not None:
        kit.primary_color = body.primary_color
    if body.secondary_color is not None:
        kit.secondary_color = body.secondary_color
    if body.font_primary is not None:
        kit.font_primary = body.font_primary
    if body.agent_name is not None:
        kit.agent_name = body.agent_name
    if body.brokerage_name is not None:
        kit.brokerage_name = body.brokerage_name
    if body.raw_config is not None:
        kit.raw_config = body.raw_config

    await db.commit()
    await db.refresh(kit)
    return kit


@router.post("/logo-upload-url")
async def get_logo_upload_url(
    current_user: User = Depends(get_current_user),
):
    """Get a presigned S3 URL for uploading a brand logo."""
    storage = StorageService()
    key = f"brand-kits/{current_user.tenant_id}/logo-{uuid.uuid4()}.png"
    presigned = storage.presigned_upload_url(
        key=key,
        content_type="image/png",
        expires_in=300,
    )
    return {"key": key, "upload": presigned}
