"""Listing import endpoints — import from third-party links (Google Drive, Dropbox, Show & Tour)."""
import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.database import get_db
from listingjet.models.listing import Listing
from listingjet.models.user import User

router = APIRouter()


class ImportLinkRequest(BaseModel):
    url: str


class ImportLinkResponse(BaseModel):
    import_id: uuid.UUID
    platform: str
    status: str


class ImportStatusResponse(BaseModel):
    import_id: uuid.UUID
    status: str
    platform: str
    total_files: int
    completed_files: int
    error_message: str | None


async def _run_link_import_background(
    listing_id: str,
    tenant_id: str,
    url: str,
    platform: str,
    import_job_id: str,
) -> None:
    """Background task that runs the link import activity."""
    from listingjet.activities.pipeline import LinkImportParams, run_link_import

    params = LinkImportParams(
        listing_id=listing_id,
        tenant_id=tenant_id,
        url=url,
        platform=platform,
        import_job_id=import_job_id,
    )
    await run_link_import(params)


@router.post("/{listing_id}/import-link", response_model=ImportLinkResponse)
async def import_from_link_endpoint(
    listing_id: uuid.UUID,
    body: ImportLinkRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start importing photos from a third-party delivery link (Google Drive, Show & Tour)."""
    from listingjet.models.import_job import ImportJob
    from listingjet.services.link_import import detect_platform

    # Verify listing belongs to tenant
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    platform = detect_platform(body.url)
    if not platform:
        raise HTTPException(
            status_code=400,
            detail="Unsupported link. Supported platforms: Google Drive, Dropbox, Show & Tour.",
        )

    # Create ImportJob record
    job = ImportJob(
        id=uuid.uuid4(),
        listing_id=listing_id,
        tenant_id=current_user.tenant_id,
        url=body.url,
        platform=platform,
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Fire-and-forget background task
    asyncio.create_task(
        _run_link_import_background(
            listing_id=str(listing_id),
            tenant_id=str(current_user.tenant_id),
            url=body.url,
            platform=platform,
            import_job_id=str(job.id),
        )
    )

    return ImportLinkResponse(
        import_id=job.id,
        platform=platform,
        status="started",
    )


@router.get("/{listing_id}/import-status/{import_id}", response_model=ImportStatusResponse)
async def get_import_status(
    listing_id: uuid.UUID,
    import_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check the status of a link-import job."""
    from listingjet.models.import_job import ImportJob

    # Verify listing belongs to tenant
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    job = await db.get(ImportJob, import_id)
    if not job or job.listing_id != listing_id:
        raise HTTPException(status_code=404, detail="Import job not found")

    return ImportStatusResponse(
        import_id=job.id,
        status=job.status,
        platform=job.platform,
        total_files=job.total_files or 0,
        completed_files=job.completed_files or 0,
        error_message=job.error_message,
    )
