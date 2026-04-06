"""Credit system service — atomic deduction, refunds, rollover, balance queries.

Pricing v3: Dual-pool credit tracking (granted vs purchased).
- Granted credits come from plan subscriptions and are subject to rollover caps.
- Purchased credits come from top-up bundles and never expire.
- FIFO: granted credits are consumed first, then purchased.
"""
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import redis as redis_lib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.credit_account import CreditAccount
from listingjet.models.credit_transaction import CreditTransaction

logger = logging.getLogger(__name__)

_LOW_CREDIT_TTL = 86400  # 24 hours


def _get_redis():
    from listingjet.config import settings
    return redis_lib.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)


class InsufficientCreditsError(Exception):
    pass


@dataclass
class CreditBalance:
    balance: int
    granted_balance: int
    purchased_balance: int
    rollover_balance: int
    rollover_cap: int
    period_start: datetime
    period_end: datetime


class CreditService:

    async def get_balance(self, session: AsyncSession, tenant_id: uuid.UUID) -> CreditBalance:
        account = await self._get_account(session, tenant_id)
        return CreditBalance(
            balance=account.balance,
            granted_balance=account.granted_balance,
            purchased_balance=account.purchased_balance,
            rollover_balance=account.rollover_balance,
            rollover_cap=account.rollover_cap,
            period_start=account.period_start,
            period_end=account.period_end,
        )

    async def has_sufficient_credits(self, session: AsyncSession, tenant_id: uuid.UUID, amount: int) -> bool:
        account = await self._get_account(session, tenant_id)
        return account.balance >= amount

    async def deduct_credits(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        amount: int,
        transaction_type: str,
        reference_type: str,
        reference_id: str,
        description: str = "",
    ) -> CreditTransaction:
        """Atomically deduct credits using FIFO (granted first, then purchased)."""
        # Idempotency check
        existing = await session.execute(
            select(CreditTransaction).where(
                CreditTransaction.reference_type == reference_type,
                CreditTransaction.reference_id == reference_id,
                CreditTransaction.transaction_type == transaction_type,
                CreditTransaction.amount < 0,
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Credits already deducted for {reference_type}:{reference_id}")

        account = await self._get_account_for_update(session, tenant_id)

        if account.balance < amount:
            raise InsufficientCreditsError(
                f"Need {amount} credits, have {account.balance}"
            )

        # FIFO: deduct from granted first, then purchased
        remaining = amount
        from_granted = min(remaining, account.granted_balance)
        remaining -= from_granted
        from_purchased = remaining  # whatever is left comes from purchased

        account.granted_balance -= from_granted
        account.purchased_balance -= from_purchased
        account.balance -= amount

        txn = CreditTransaction(
            tenant_id=tenant_id,
            account_id=account.id,
            amount=-amount,
            balance_after=account.balance,
            transaction_type=transaction_type,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
        )
        session.add(txn)

        # Low-credit alert
        if account.balance < 3:
            self._send_low_credit_alert(session, tenant_id, account.balance)

        return txn

    def _send_low_credit_alert(self, session, tenant_id, balance):
        dedup_key = f"low_credit_sent:{tenant_id}"
        try:
            r = _get_redis()
            if r.set(dedup_key, "1", nx=True, ex=_LOW_CREDIT_TTL):
                import asyncio
                asyncio.ensure_future(self._send_low_credit_email(session, tenant_id, balance))
        except Exception:
            logger.exception("credits_low alert failed for tenant %s", tenant_id)

    async def _send_low_credit_email(self, session, tenant_id, balance):
        try:
            from listingjet.models.user import User, UserRole
            from listingjet.services.email import get_email_service
            admin_result = await session.execute(
                select(User).where(
                    User.tenant_id == tenant_id,
                    User.role == UserRole.ADMIN,
                ).limit(1)
            )
            admin_user = admin_result.scalar_one_or_none()
            if admin_user:
                email_svc = get_email_service()
                email_svc.send_notification(
                    admin_user.email,
                    "credits_low",
                    name=admin_user.name or "there",
                    balance=str(balance),
                    buy_url="https://app.listingjet.com/billing/credits",
                )
        except Exception:
            logger.exception("credits_low email failed for tenant %s", tenant_id)

    async def add_credits(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        amount: int,
        transaction_type: str,
        reference_type: str | None = None,
        reference_id: str | None = None,
        description: str = "",
    ) -> CreditTransaction:
        """Add credits to a tenant's balance. Routes to the correct pool."""
        # Idempotency for purchases/grants
        if reference_id:
            existing = await session.execute(
                select(CreditTransaction).where(
                    CreditTransaction.reference_id == reference_id,
                    CreditTransaction.transaction_type == transaction_type,
                    CreditTransaction.amount > 0,
                ).limit(1)
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Credits already granted for {reference_id}")

        account = await self._get_account_for_update(session, tenant_id)

        account.balance += amount

        # Route to correct pool based on transaction type
        if transaction_type in ("purchase", "refund"):
            account.purchased_balance += amount
        else:
            # plan_grant, rollover, admin_adjustment, bonus
            account.granted_balance += amount

        txn = CreditTransaction(
            tenant_id=tenant_id,
            account_id=account.id,
            amount=amount,
            balance_after=account.balance,
            transaction_type=transaction_type,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
        )
        session.add(txn)
        return txn

    async def refund_credits(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        listing_id: str,
    ) -> CreditTransaction | None:
        """Refund credits for a listing. Returns None if no deduction found."""
        result = await session.execute(
            select(CreditTransaction).where(
                CreditTransaction.tenant_id == tenant_id,
                CreditTransaction.reference_type == "listing",
                CreditTransaction.reference_id == listing_id,
                CreditTransaction.transaction_type == "listing_debit",
            ).limit(1)
        )
        original = result.scalar_one_or_none()
        if not original:
            return None

        refund_amount = abs(original.amount)
        return await self.add_credits(
            session, tenant_id, refund_amount,
            transaction_type="refund",
            reference_type="listing",
            reference_id=listing_id,
            description=f"Refund for cancelled listing {listing_id}",
        )

    async def process_period_renewal(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        included_credits: int,
    ) -> None:
        """Handle billing period rollover.

        Only granted credits are subject to the rollover cap.
        Purchased credits are never expired.
        """
        account = await self._get_account_for_update(session, tenant_id)

        # Expire granted credits above rollover cap
        rollover_granted = min(account.granted_balance, account.rollover_cap)
        expired = account.granted_balance - rollover_granted

        if expired > 0:
            account.granted_balance = rollover_granted
            account.balance -= expired
            session.add(CreditTransaction(
                tenant_id=tenant_id,
                account_id=account.id,
                amount=-expired,
                balance_after=account.balance,
                transaction_type="expiry",
                description=f"Expired {expired} granted credits at period end",
            ))

        # Grant new included credits (go to granted pool)
        if included_credits > 0:
            account.granted_balance += included_credits
            account.balance += included_credits
            session.add(CreditTransaction(
                tenant_id=tenant_id,
                account_id=account.id,
                amount=included_credits,
                balance_after=account.balance,
                transaction_type="plan_grant",
                description=f"Monthly grant of {included_credits} credits",
            ))

        account.rollover_balance = rollover_granted
        now = datetime.now(timezone.utc)
        account.period_start = now
        account.period_end = now + timedelta(days=30)

    async def get_transactions(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CreditTransaction]:
        result = await session.execute(
            select(CreditTransaction)
            .where(CreditTransaction.tenant_id == tenant_id)
            .order_by(CreditTransaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def ensure_account(self, session: AsyncSession, tenant_id: uuid.UUID, rollover_cap: int = 0) -> CreditAccount:
        """Get or create a credit account for a tenant."""
        account = (await session.execute(
            select(CreditAccount).where(CreditAccount.tenant_id == tenant_id)
        )).scalar_one_or_none()
        if not account:
            account = CreditAccount(
                tenant_id=tenant_id,
                balance=0,
                granted_balance=0,
                purchased_balance=0,
                rollover_cap=rollover_cap,
            )
            session.add(account)
            await session.flush()
        return account

    async def _get_account(self, session: AsyncSession, tenant_id: uuid.UUID) -> CreditAccount:
        result = await session.execute(
            select(CreditAccount).where(CreditAccount.tenant_id == tenant_id)
        )
        account = result.scalar_one_or_none()
        if not account:
            raise ValueError(f"No credit account for tenant {tenant_id}")
        return account

    async def _get_account_for_update(self, session: AsyncSession, tenant_id: uuid.UUID) -> CreditAccount:
        result = await session.execute(
            select(CreditAccount)
            .where(CreditAccount.tenant_id == tenant_id)
            .with_for_update()
        )
        account = result.scalar_one_or_none()
        if not account:
            raise ValueError(f"No credit account for tenant {tenant_id}")
        return account
