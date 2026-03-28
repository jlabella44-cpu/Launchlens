import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from launchlens.api.deps import get_current_user
from launchlens.api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from launchlens.api.schemas.notifications import NotificationPreferenceResponse, NotificationPreferenceUpdate
from launchlens.database import get_db
from launchlens.models.notification_preference import NotificationPreference
from launchlens.models.tenant import Tenant
from launchlens.models.user import User, UserRole
from launchlens.services.auth import create_access_token, hash_password, verify_password_constant_time

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    tenant = Tenant(id=uuid.uuid4(), name=body.company_name, plan="starter")
    db.add(tenant)
    await db.flush()

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password(body.password),
        name=body.name,
        role=UserRole.ADMIN,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info("auth.register email=%s tenant=%s", email, tenant.id)
    return TokenResponse(access_token=create_access_token(user))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    # Constant-time comparison: always run bcrypt even if user not found
    password_valid = verify_password_constant_time(
        body.password, user.password_hash if user else None
    )
    if not user or not password_valid:
        logger.warning("auth.login_failed email=%s", email)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    logger.info("auth.login_success email=%s user=%s", email, user.id)
    return TokenResponse(access_token=create_access_token(user))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/me/notifications", response_model=NotificationPreferenceResponse)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pref = (
        await db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if not pref:
        return NotificationPreferenceResponse()  # defaults (all True)
    return pref


@router.patch("/me/notifications", response_model=NotificationPreferenceResponse)
async def update_notification_preferences(
    body: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pref = (
        await db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == current_user.id)
        )
    ).scalar_one_or_none()

    if not pref:
        pref = NotificationPreference(user_id=current_user.id)
        db.add(pref)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(pref, field, value)

    await db.commit()
    await db.refresh(pref)
    return pref
