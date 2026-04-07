"""Social accounts CRUD router — stubbed for future OAuth."""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from listingjet.api.deps import get_current_user
from listingjet.api.schemas.social import CreateSocialAccountRequest, SocialAccountResponse
from listingjet.database import get_db
from listingjet.models.social_account import SocialAccount
from listingjet.models.user import User

router = APIRouter()

@router.get("", response_model=list[SocialAccountResponse])
async def list_social_accounts(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.user_id == current_user.id, SocialAccount.tenant_id == current_user.tenant_id,
        ).order_by(SocialAccount.created_at)
    )
    return [SocialAccountResponse.model_validate(a) for a in result.scalars().all()]

@router.post("", status_code=201, response_model=SocialAccountResponse)
async def create_or_update_social_account(
    body: CreateSocialAccountRequest, current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(
        select(SocialAccount).where(SocialAccount.user_id == current_user.id, SocialAccount.platform == body.platform)
    )).scalar_one_or_none()
    if existing:
        existing.platform_username = body.platform_username
        existing.status = "pending"
        await db.commit()
        await db.refresh(existing)
        return SocialAccountResponse.model_validate(existing)
    account = SocialAccount(
        tenant_id=current_user.tenant_id, user_id=current_user.id,
        platform=body.platform, platform_username=body.platform_username, status="pending",
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return SocialAccountResponse.model_validate(account)

@router.delete("/{account_id}", status_code=200)
async def delete_social_account(
    account_id: uuid.UUID, current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = (await db.execute(
        select(SocialAccount).where(SocialAccount.id == account_id, SocialAccount.user_id == current_user.id)
    )).scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Social account not found")
    await db.delete(account)
    await db.commit()
    return {"deleted": True}
