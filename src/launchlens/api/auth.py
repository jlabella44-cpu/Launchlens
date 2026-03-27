import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from launchlens.database import get_db
from launchlens.models.tenant import Tenant
from launchlens.models.user import User, UserRole
from launchlens.services.auth import hash_password, verify_password, create_access_token
from launchlens.api.schemas.auth import RegisterRequest, LoginRequest, TokenResponse

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    tenant = Tenant(id=uuid.uuid4(), name=body.company_name, plan="starter")
    db.add(tenant)
    await db.flush()

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name,
        role=UserRole.ADMIN,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return TokenResponse(access_token=create_access_token(user))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return TokenResponse(access_token=create_access_token(user))
