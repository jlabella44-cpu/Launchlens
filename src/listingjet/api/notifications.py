"""Notifications router — list, mark read."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.social import NotificationListResponse, NotificationResponse
from listingjet.database import get_db
from listingjet.models.notification import Notification
from listingjet.models.user import User

router = APIRouter()

@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    unread: bool = False, limit: int = 20,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    query = select(Notification).where(
        Notification.user_id == current_user.id, Notification.tenant_id == current_user.tenant_id,
    )
    if unread:
        query = query.where(Notification.read_at.is_(None))
    query = query.order_by(Notification.created_at.desc()).limit(min(limit, 50))
    result = await db.execute(query)
    items = result.scalars().all()

    count_result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id, Notification.tenant_id == current_user.tenant_id,
            Notification.read_at.is_(None),
        )
    )
    unread_count = count_result.scalar() or 0
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in items], unread_count=unread_count,
    )

@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: uuid.UUID, current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notif = (await db.execute(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == current_user.id)
    )).scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notif.read_at is None:
        notif.read_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(notif)
    return NotificationResponse.model_validate(notif)

@router.patch("/read-all")
async def mark_all_read(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification).where(
            Notification.user_id == current_user.id, Notification.tenant_id == current_user.tenant_id,
            Notification.read_at.is_(None),
        ).values(read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"status": "ok"}
