import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.database import get_db
from listingjet.models.listing import Listing
from listingjet.models.social_content import SocialContent
from listingjet.models.user import User

router = APIRouter(tags=["social-content"])


def _captions(raw: str) -> dict[str, str]:
    try:
        hooks = json.loads(raw)
    except (TypeError, ValueError):
        return {"storyteller": raw} if raw else {}
    if isinstance(hooks, list):
        return {h["style"]: h.get("caption", "") for h in hooks if isinstance(h, dict) and h.get("style")}
    return {"storyteller": raw}


@router.get("/{listing_id}/social-content")
async def get_social_content(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = (await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == current_user.tenant_id)
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    rows = (await db.execute(
        select(SocialContent).where(SocialContent.listing_id == listing_id)
    )).scalars().all()
    by_platform = {r.platform: r for r in rows}
    ig, fb, tt = by_platform.get("instagram"), by_platform.get("facebook"), by_platform.get("tiktok")
    return {
        "instagram_captions": _captions(ig.caption) if ig else {},
        "facebook_captions": _captions(fb.caption) if fb else {},
        "tiktok_caption": tt.caption if tt else None,
        "hashtags": list(ig.hashtags or []) if ig else [],
        "cta": {"instagram": ig.cta if ig else None, "facebook": fb.cta if fb else None},
        "generated": bool(rows),
    }
