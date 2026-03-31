"""Credit system service — atomic deduction, refunds, rollover, balance queries."""
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.config.tiers import TIER_CREDITS
from listingjet.models.credit_account import CreditAccount
from listingjet.models.credit_transaction import CreditTransaction


class InsufficientCreditsError(Exception):
    pass


@dataclass
class CreditBalance:
    balance: int
    rollover_balance: int
    rollover_cap: int
    period_start: datetime
    period_end: datetime


class CreditService:

    async def get_balance(self, session: AsyncSession, tenant_id: uuid.UUID) -> CreditBalance:
        account = await self._get_account(session, tenant_id)
        return CreditBalance(
            balance=account.balance,
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
        """Atomically deduct credits. Uses SELECT FOR UPDATE to prevent races."""
        # Idempotency: check if this deduction already happened
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
        return txn

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
        """Add credits to a tenant's balance."""
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
        # Find original deduction
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
        """Handle billing period rollover: cap old credits, grant new ones."""
        account = await self._get_account_for_update(session, tenant_id)

        # Expire credits above rollover cap
        rollover_amount = min(account.balance, account.rollover_cap)
        expired = account.balance - rollover_amount

        if expired > 0:
            session.add(CreditTransaction(
                tenant_id=tenant_id,
                account_id=account.id,
                amount=-expired,
                balance_after=rollover_amount,
                transaction_type="expiry",
                description=f"Expired {expired} credits at period end",
            ))

        # Grant new included credits
        new_balance = rollover_amount + included_credits
        if included_credits > 0:
            session.add(CreditTransaction(
                tenant_id=tenant_id,
                account_id=account.id,
                amount=included_credits,
                balance_after=new_balance,
                transaction_type="plan_grant",
                description=f"Monthly grant of {included_credits} credits",
            ))

        account.balance = new_balance
        account.rollover_balance = rollover_amount
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
