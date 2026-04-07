import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_db_admin
from listingjet.api.schemas.demo import (
    DemoCreateRequest,
    DemoCreateResponse,
    DemoUploadRequest,
    DemoUploadResponse,
    DemoViewResponse,
)
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing, ListingState
from listingjet.services.rate_limiter import RateLimiter
from listingjet.services.storage import get_storage

router = APIRouter()

_DEMO_TTL_HOURS = 24
_DEMO_PHOTO_MIN = 5
_DEMO_PHOTO_MAX = 50
_DEMO_RATE_LIMIT_PER_WEEK = 1
_DEMO_TENANT_ID = uuid.UUID(int=0)  # placeholder tenant for demo listings

_demo_limiter: RateLimiter | None = None


def _get_demo_limiter() -> RateLimiter:
    global _demo_limiter
    if _demo_limiter is None:
        _demo_limiter = RateLimiter(
            key_prefix="demo",
            capacity=_DEMO_RATE_LIMIT_PER_WEEK,
            refill_rate=_DEMO_RATE_LIMIT_PER_WEEK / (7 * 86400),
        )
    return _demo_limiter


def _get_client_ip(request: Request) -> str:
    from listingjet.middleware.rate_limit import TRUSTED_PROXY_COUNT
    if TRUSTED_PROXY_COUNT > 0:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            parts = [p.strip() for p in forwarded.split(",")]
            idx = max(0, len(parts) - TRUSTED_PROXY_COUNT)
            return parts[idx]
    return request.client.host if request.client else "unknown"


@router.post("/create", status_code=201, response_model=DemoCreateResponse)
async def demo_create(
    body: DemoCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_admin),
):
    """Create a demo listing and return presigned S3 upload URLs. No auth required."""
    ip = _get_client_ip(request)
    limiter = _get_demo_limiter()
    if not limiter.acquire(key=ip, cost=1):
        raise HTTPException(
            status_code=429,
            detail="Demo limit reached. Try again next week.",
        )

    count = body.photo_count
    if count < _DEMO_PHOTO_MIN or count > _DEMO_PHOTO_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"Photo count must be between {_DEMO_PHOTO_MIN} and {_DEMO_PHOTO_MAX}, got {count}",
        )

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=_DEMO_TTL_HOURS)

    listing = Listing(
        tenant_id=_DEMO_TENANT_ID,
        address={},
        metadata_={},
        state=ListingState.DEMO,
        is_demo=True,
        demo_expires_at=expires_at,
    )
    db.add(listing)
    await db.flush()

    storage = get_storage()
    upload_urls = []
    for i in range(count):
        key = f"demos/{listing.id}/{i:03d}.jpg"
        try:
            presigned = storage.presigned_upload_url(
                key=key,
                content_type="image/jpeg",
                expires_in=900,
            )
            upload_urls.append({
                "index": i,
                "key": key,
                "upload_url": presigned,
                "content_type": "image/jpeg",
            })
        except Exception:
            # Also accept PNG
            try:
                presigned = storage.presigned_upload_url(
                    key=key.replace(".jpg", ".png"),
                    content_type="image/png",
                    expires_in=900,
                )
                upload_urls.append({
                    "index": i,
                    "key": key.replace(".jpg", ".png"),
                    "upload_url": presigned,
                    "content_type": "image/png",
                })
            except Exception:
                upload_urls.append({
                    "index": i,
                    "key": key,
                    "upload_url": None,
                    "content_type": "image/jpeg",
                })

    await db.commit()

    return DemoCreateResponse(
        demo_id=listing.id,
        upload_urls=upload_urls,
        expires_at=expires_at,
    )


@router.post("/{demo_id}/finalize", status_code=200, response_model=DemoUploadResponse)
async def demo_finalize(
    demo_id: uuid.UUID,
    body: DemoUploadRequest,
    db: AsyncSession = Depends(get_db_admin),
):
    """Finalize a demo listing after files have been uploaded to S3."""
    listing = await db.get(Listing, demo_id)
    if not listing or not listing.is_demo:
        raise HTTPException(status_code=404, detail="Demo listing not found")

    if listing.demo_expires_at and listing.demo_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Demo listing expired")

    for fp in body.file_paths:
        asset = Asset(
            tenant_id=_DEMO_TENANT_ID,
            listing_id=listing.id,
            file_path=fp,
            file_hash=hashlib.sha256(fp.encode()).hexdigest(),
            state="uploaded",
        )
        db.add(asset)

    await db.commit()

    return DemoUploadResponse(
        demo_id=listing.id,
        photo_count=len(body.file_paths),
        expires_at=listing.demo_expires_at,
    )


@router.post("/upload", status_code=201, response_model=DemoUploadResponse)
async def demo_upload(
    body: DemoUploadRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_admin),
):
    """Create a demo listing with uploaded photos. No auth required. Rate limited: 1/IP/week."""
    ip = _get_client_ip(request)
    limiter = _get_demo_limiter()
    if not limiter.acquire(key=ip, cost=1):
        raise HTTPException(
            status_code=429,
            detail="Demo limit reached. Try again next week.",
        )

    count = len(body.file_paths)
    if count < _DEMO_PHOTO_MIN or count > _DEMO_PHOTO_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"Photo count must be between {_DEMO_PHOTO_MIN} and {_DEMO_PHOTO_MAX}, got {count}",
        )

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=_DEMO_TTL_HOURS)

    listing = Listing(
        tenant_id=_DEMO_TENANT_ID,
        address={},
        metadata_={},
        state=ListingState.DEMO,
        is_demo=True,
        demo_expires_at=expires_at,
    )
    db.add(listing)
    await db.flush()

    for fp in body.file_paths:
        asset = Asset(
            tenant_id=_DEMO_TENANT_ID,
            listing_id=listing.id,
            file_path=fp,
            file_hash=hashlib.sha256(fp.encode()).hexdigest(),
            state="uploaded",
        )
        db.add(asset)

    await db.commit()

    return DemoUploadResponse(
        demo_id=listing.id,
        photo_count=count,
        expires_at=expires_at,
    )


@router.get("/{demo_id}", response_model=DemoViewResponse)
async def demo_view(
    demo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_admin),
):
    """View a demo listing. No auth required. Returns 410 if expired."""
    listing = await db.get(Listing, demo_id)
    if not listing or not listing.is_demo:
        raise HTTPException(status_code=404, detail="Demo listing not found")

    if listing.demo_expires_at and listing.demo_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Demo listing expired")

    # Fetch associated assets
    result = await db.execute(
        select(Asset).where(Asset.listing_id == demo_id)
    )
    assets = result.scalars().all()
    photos = [{"file_path": a.file_path, "state": a.state} for a in assets]

    return DemoViewResponse(
        demo_id=listing.id,
        address=listing.address,
        state=listing.state.value if isinstance(listing.state, ListingState) else listing.state,
        is_demo=listing.is_demo,
        photos=photos,
    )


@router.post("/{demo_id}/claim")
async def demo_claim(
    demo_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_admin),
):
    """Claim a demo listing. Requires auth (tenant_id from middleware)."""
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Authentication required to claim a demo")

    listing = await db.get(Listing, demo_id)
    if not listing or not listing.is_demo:
        raise HTTPException(status_code=404, detail="Demo listing not found")

    if listing.demo_expires_at and listing.demo_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Demo listing expired")

    listing.tenant_id = uuid.UUID(tenant_id)
    listing.is_demo = False
    listing.demo_expires_at = None
    listing.state = ListingState.UPLOADING

    # Also update assets to the new tenant
    result = await db.execute(
        select(Asset).where(Asset.listing_id == demo_id)
    )
    assets = result.scalars().all()
    for asset in assets:
        asset.tenant_id = uuid.UUID(tenant_id)

    await db.commit()

    return {"listing_id": str(listing.id), "state": listing.state.value, "claimed": True}
