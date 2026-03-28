"""
Credit service — manages tenant credit balances and transactions.

All write operations are idempotent when called with the same reference_id.
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from launchlens.models.credit_transaction import CreditTransaction
from launchlens.models.tenant import Tenant

logger = logging.getLogger(__name__)

# Plan tier → (included_credits, rollover_cap)
TIER_CREDITS = {
    "lite": (0, 0),
    "starter": (10, 5),
    "pro": (50, 25),
    "enterprise": (200, 100),
}


class CreditService:
    """Stateless service — pass an AsyncSession per call."""

    async def _is_duplicate(self, db: AsyncSession, reference_id: str) -> bool:
        """Check if a transaction with this reference_id already exists."""
        if not reference_id:
            return False
        result = await db.execute(
            select(CreditTransaction).where(CreditTransaction.reference_id == reference_id).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _record(
        self,
        db: AsyncSession,
        tenant: Tenant,
        amount: int,
        transaction_type: str,
        reference_type: str | None = None,
        reference_id: str | None = None,
        description: str | None = None,
    ) -> CreditTransaction:
        """Record a credit transaction and update tenant balance."""
        tenant.credit_balance += amount
        txn = CreditTransaction(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            amount=amount,
            balance_after=tenant.credit_balance,
            transaction_type=transaction_type,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
        )
        db.add(txn)
        return txn

    async def add_credits(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        amount: int,
        transaction_type: str = "purchase",
        reference_type: str | None = None,
        reference_id: str | None = None,
        description: str | None = None,
    ) -> CreditTransaction | None:
        """Add credits to a tenant's balance. Idempotent on reference_id."""
        if reference_id and await self._is_duplicate(db, reference_id):
            logger.info("Duplicate credit add skipped: ref=%s", reference_id)
            return None

        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            logger.warning("add_credits: tenant %s not found", tenant_id)
            return None

        txn = await self._record(
            db, tenant, amount,
            transaction_type=transaction_type,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
        )
        await db.flush()
        logger.info("Credits added: tenant=%s amount=%d balance=%d ref=%s", tenant_id, amount, tenant.credit_balance, reference_id)
        return txn

    async def deduct_credits(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        amount: int,
        reference_type: str | None = None,
        reference_id: str | None = None,
        description: str | None = None,
    ) -> CreditTransaction | None:
        """Deduct credits. Returns None if insufficient balance or duplicate."""
        if reference_id and await self._is_duplicate(db, reference_id):
            logger.info("Duplicate deduction skipped: ref=%s", reference_id)
            return None

        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            return None

        if tenant.credit_balance < amount:
            logger.warning("Insufficient credits: tenant=%s balance=%d requested=%d", tenant_id, tenant.credit_balance, amount)
            return None

        txn = await self._record(
            db, tenant, -amount,
            transaction_type="deduction",
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
        )
        await db.flush()
        return txn

    async def process_period_renewal(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        included_credits: int,
        reference_id: str | None = None,
    ) -> dict:
        """Process subscription period renewal: rollover capped credits + grant included.

        Returns dict with old_balance, rolled_over, granted, new_balance.
        """
        if reference_id and await self._is_duplicate(db, reference_id):
            logger.info("Duplicate renewal skipped: ref=%s", reference_id)
            return {"skipped": True}

        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            return {"error": "tenant_not_found"}

        old_balance = tenant.credit_balance

        # Cap rollover
        rolled_over = min(old_balance, tenant.rollover_cap)
        expired = old_balance - rolled_over

        # Record expiry if any credits were lost
        if expired > 0:
            await self._record(
                db, tenant, -expired,
                transaction_type="expiry",
                reference_type="period_renewal",
                description=f"Period renewal: {expired} credits expired (cap={tenant.rollover_cap})",
            )

        # Grant included credits
        if included_credits > 0:
            await self._record(
                db, tenant, included_credits,
                transaction_type="grant",
                reference_type="stripe_event",
                reference_id=reference_id,
                description=f"Subscription renewal: {included_credits} included credits",
            )

        await db.flush()
        new_balance = tenant.credit_balance

        logger.info(
            "Period renewal: tenant=%s old=%d rolled=%d expired=%d granted=%d new=%d",
            tenant_id, old_balance, rolled_over, expired, included_credits, new_balance,
        )
        return {
            "old_balance": old_balance,
            "rolled_over": rolled_over,
            "expired": expired,
            "granted": included_credits,
            "new_balance": new_balance,
        }

    async def get_balance(self, db: AsyncSession, tenant_id: uuid.UUID) -> int:
        """Get current credit balance."""
        tenant = await db.get(Tenant, tenant_id)
        return tenant.credit_balance if tenant else 0
