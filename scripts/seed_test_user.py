"""Seed test users for local development.

Usage:
    uv run python scripts/seed_test_user.py

Creates two users on the same tenant:

  Admin:
    Email:    demo@listingjet.com
    Password: DemoPass1!
    Role:     admin

  Regular user:
    Email:    agent@listingjet.com
    Password: DemoPass1!
    Role:     agent
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

PASSWORD = "DemoPass1!"
COMPANY = "ListingJet Demo"

USERS = [
    {
        "email": "demo@listingjet.com",
        "name": "Demo Admin",
        "role": UserRole.ADMIN,
    },
    {
        "email": "agent@listingjet.com",
        "name": "Demo Agent",
        "role": UserRole.AGENT,
    },
]


async def main():
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        # Check if tenant already exists (keyed off first user)
        existing = (
            await session.execute(select(User).where(User.email == USERS[0]["email"]))
        ).scalar_one_or_none()

        if existing:
            tenant_id = existing.tenant_id
            print(f"Tenant already exists: {tenant_id}")
        else:
            tenant_id = uuid.uuid4()
            tenant = Tenant(
                id=tenant_id,
                name=COMPANY,
                plan="active_agent",
                plan_tier="active_agent",
                billing_model="credit",
                per_listing_credit_cost=12,
                credit_balance=75,
                included_credits=75,
                rollover_cap=50,
            )
            session.add(tenant)
            await session.flush()

            credit_account = CreditAccount(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                balance=75,
                granted_balance=75,
                purchased_balance=0,
                rollover_cap=50,
            )
            session.add(credit_account)
            print(f"Created tenant: {COMPANY} ({tenant_id})")

        # Create each user if they don't exist
        for user_info in USERS:
            existing_user = (
                await session.execute(select(User).where(User.email == user_info["email"]))
            ).scalar_one_or_none()

            if existing_user:
                print(f"  Already exists: {user_info['email']} ({existing_user.role.value})")
                continue

            user = User(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                email=user_info["email"],
                password_hash=hash_password(PASSWORD),
                name=user_info["name"],
                role=user_info["role"],
                consent_at=datetime.now(timezone.utc),
                consent_version="2026-04-03",
            )
            session.add(user)
            print(f"  Created: {user_info['email']} ({user_info['role'].value})")

        await session.commit()

        print()
        print("Test accounts ready:")
        print()
        print("  Admin (full access + review queue + admin dashboard):")
        print(f"    Email:    {USERS[0]['email']}")
        print(f"    Password: {PASSWORD}")
        print()
        print("  Agent (regular user — own listings only, no review/admin):")
        print(f"    Email:    {USERS[1]['email']}")
        print(f"    Password: {PASSWORD}")
        print()
        print(f"  Shared tenant: {COMPANY} (Pro plan, 50 credits)")


if __name__ == "__main__":
    asyncio.run(main())
