"""Seed a test user for local development.

Usage:
    uv run python scripts/seed_test_user.py

Creates:
    Email:    demo@listingjet.com
    Password: DemoPass1!
    Plan:     Pro (active_agent tier)
    Role:     Admin
"""
import asyncio
import uuid
from datetime import datetime, timezone

from listingjet.config import settings  # noqa: F401 — validates env
from listingjet.database import AsyncSessionLocal
from listingjet.models.credit_account import CreditAccount
from listingjet.models.tenant import Tenant
from listingjet.models.user import User, UserRole
from listingjet.services.auth import hash_password

EMAIL = "demo@listingjet.com"
PASSWORD = "DemoPass1!"
NAME = "Demo User"
COMPANY = "ListingJet Demo"
PLAN = "pro"
PLAN_TIER = "active_agent"


async def main():
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        # Check if user already exists
        existing = (
            await session.execute(select(User).where(User.email == EMAIL))
        ).scalar_one_or_none()

        if existing:
            print(f"Test user already exists: {EMAIL}")
            print(f"  Password: {PASSWORD}")
            print(f"  User ID:  {existing.id}")
            print(f"  Tenant:   {existing.tenant_id}")
            return

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        tenant = Tenant(
            id=tenant_id,
            name=COMPANY,
            plan=PLAN,
            plan_tier=PLAN_TIER,
            billing_model="credit",
            per_listing_credit_cost=1,
            credit_balance=50,
            included_credits=50,
            rollover_cap=25,
        )
        session.add(tenant)
        await session.flush()

        credit_account = CreditAccount(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            balance=50,
            rollover_cap=25,
        )
        session.add(credit_account)

        user = User(
            id=user_id,
            tenant_id=tenant_id,
            email=EMAIL,
            password_hash=hash_password(PASSWORD),
            name=NAME,
            role=UserRole.ADMIN,
            consent_at=datetime.now(timezone.utc),
            consent_version="2026-04-03",
        )
        session.add(user)
        await session.commit()

        print("Test user created successfully!")
        print()
        print(f"  Email:     {EMAIL}")
        print(f"  Password:  {PASSWORD}")
        print(f"  Name:      {NAME}")
        print(f"  Role:      admin")
        print(f"  Plan:      {PLAN} ({PLAN_TIER})")
        print(f"  Credits:   50")
        print(f"  User ID:   {user_id}")
        print(f"  Tenant ID: {tenant_id}")


if __name__ == "__main__":
    asyncio.run(main())
