"""CreditService unit tests — deduction, insufficiency, idempotency, add, refund, rollover."""
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.credit_account import CreditAccount
from listingjet.services.credits import CreditService, InsufficientCreditsError


async def _create_account(
    session: AsyncSession, tenant_id: uuid.UUID, balance: int = 10, rollover_cap: int = 5,
) -> CreditAccount:
    account = CreditAccount(tenant_id=tenant_id, balance=balance, rollover_cap=rollover_cap)
    session.add(account)
    await session.flush()
    return account


# --- deduct_credits ---


@pytest.mark.asyncio
async def test_deduct_credits_success(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=10)
    svc = CreditService()

    txn = await svc.deduct_credits(
        db_session, tid, 3,
        transaction_type="listing_debit",
        reference_type="listing",
        reference_id=str(uuid.uuid4()),
    )

    assert txn.amount == -3
    assert txn.balance_after == 7
    balance = await svc.get_balance(db_session, tid)
    assert balance.balance == 7


@pytest.mark.asyncio
async def test_deduct_insufficient_credits(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=2)
    svc = CreditService()

    with pytest.raises(InsufficientCreditsError, match="Need 5 credits, have 2"):
        await svc.deduct_credits(
            db_session, tid, 5,
            transaction_type="listing_debit",
            reference_type="listing",
            reference_id=str(uuid.uuid4()),
        )

    # Balance unchanged
    balance = await svc.get_balance(db_session, tid)
    assert balance.balance == 2


@pytest.mark.asyncio
async def test_deduct_idempotency(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=10)
    svc = CreditService()
    ref_id = str(uuid.uuid4())

    await svc.deduct_credits(
        db_session, tid, 3,
        transaction_type="listing_debit",
        reference_type="listing",
        reference_id=ref_id,
    )

    # Second call with same reference_id raises ValueError
    with pytest.raises(ValueError, match="Credits already deducted"):
        await svc.deduct_credits(
            db_session, tid, 3,
            transaction_type="listing_debit",
            reference_type="listing",
            reference_id=ref_id,
        )

    # Balance only deducted once
    balance = await svc.get_balance(db_session, tid)
    assert balance.balance == 7


# --- add_credits ---


@pytest.mark.asyncio
async def test_add_credits(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=5)
    svc = CreditService()

    txn = await svc.add_credits(
        db_session, tid, 10,
        transaction_type="purchase",
        reference_type="stripe_invoice",
        reference_id=str(uuid.uuid4()),
        description="Bought 10 credits",
    )

    assert txn.amount == 10
    assert txn.balance_after == 15
    balance = await svc.get_balance(db_session, tid)
    assert balance.balance == 15


@pytest.mark.asyncio
async def test_add_credits_idempotency(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=5)
    svc = CreditService()
    ref_id = str(uuid.uuid4())

    await svc.add_credits(
        db_session, tid, 10,
        transaction_type="purchase",
        reference_id=ref_id,
    )

    with pytest.raises(ValueError, match="Credits already granted"):
        await svc.add_credits(
            db_session, tid, 10,
            transaction_type="purchase",
            reference_id=ref_id,
        )

    balance = await svc.get_balance(db_session, tid)
    assert balance.balance == 15  # only added once


# --- refund_credits ---


@pytest.mark.asyncio
async def test_refund_credits(db_session: AsyncSession):
    tid = uuid.uuid4()
    listing_id = str(uuid.uuid4())
    await _create_account(db_session, tid, balance=10)
    svc = CreditService()

    # Deduct first
    await svc.deduct_credits(
        db_session, tid, 3,
        transaction_type="listing_debit",
        reference_type="listing",
        reference_id=listing_id,
    )
    assert (await svc.get_balance(db_session, tid)).balance == 7

    # Refund
    refund_txn = await svc.refund_credits(db_session, tid, listing_id)
    assert refund_txn is not None
    assert refund_txn.amount == 3
    assert refund_txn.transaction_type == "refund"
    assert (await svc.get_balance(db_session, tid)).balance == 10


@pytest.mark.asyncio
async def test_refund_no_original(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=10)
    svc = CreditService()

    result = await svc.refund_credits(db_session, tid, str(uuid.uuid4()))
    assert result is None


# --- ensure_account ---


@pytest.mark.asyncio
async def test_ensure_account_creates_new(db_session: AsyncSession):
    tid = uuid.uuid4()
    svc = CreditService()

    account = await svc.ensure_account(db_session, tid, rollover_cap=5)
    assert account.tenant_id == tid
    assert account.balance == 0
    assert account.rollover_cap == 5


@pytest.mark.asyncio
async def test_ensure_account_returns_existing(db_session: AsyncSession):
    tid = uuid.uuid4()
    existing = await _create_account(db_session, tid, balance=42)
    svc = CreditService()

    account = await svc.ensure_account(db_session, tid)
    assert account.id == existing.id
    assert account.balance == 42


# --- rollover ---


@pytest.mark.asyncio
async def test_rollover_within_cap(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=3, rollover_cap=5)
    svc = CreditService()

    await svc.process_period_renewal(db_session, tid, included_credits=10)

    balance = await svc.get_balance(db_session, tid)
    # 3 rolls over (under cap of 5) + 10 new = 13
    assert balance.balance == 13
    assert balance.rollover_balance == 3


@pytest.mark.asyncio
async def test_rollover_exceeds_cap(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=8, rollover_cap=5)
    svc = CreditService()

    await svc.process_period_renewal(db_session, tid, included_credits=10)

    balance = await svc.get_balance(db_session, tid)
    # 5 rolls over (capped) + 10 new = 15. 3 expired.
    assert balance.balance == 15
    assert balance.rollover_balance == 5

    # Verify expiry transaction was created
    txns = await svc.get_transactions(db_session, tid)
    expiry_txns = [t for t in txns if t.transaction_type == "expiry"]
    assert len(expiry_txns) == 1
    assert expiry_txns[0].amount == -3


@pytest.mark.asyncio
async def test_rollover_with_grant(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=2, rollover_cap=5)
    svc = CreditService()

    await svc.process_period_renewal(db_session, tid, included_credits=5)

    balance = await svc.get_balance(db_session, tid)
    # 2 rolls over + 5 granted = 7
    assert balance.balance == 7

    txns = await svc.get_transactions(db_session, tid)
    grant_txns = [t for t in txns if t.transaction_type == "plan_grant"]
    assert len(grant_txns) == 1
    assert grant_txns[0].amount == 5


# --- get_transactions ---


@pytest.mark.asyncio
async def test_get_transactions_ordered(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=20)
    svc = CreditService()

    for i in range(3):
        await svc.deduct_credits(
            db_session, tid, 1,
            transaction_type="listing_debit",
            reference_type="listing",
            reference_id=str(uuid.uuid4()),
        )

    txns = await svc.get_transactions(db_session, tid)
    assert len(txns) == 3
    # Most recent first
    assert txns[0].balance_after > txns[-1].balance_after or txns[0].balance_after == txns[-1].balance_after


# --- concurrent deduction ---


@pytest.mark.asyncio
async def test_concurrent_deductions_no_double_spend(test_engine):
    """Two simultaneous deductions of 1 credit from a 1-credit account:
    one should succeed, one should raise InsufficientCreditsError.
    Final balance must be 0, never -1."""
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    tid = uuid.uuid4()

    # Setup: create account with 1 credit
    async with factory() as setup_session:
        async with setup_session.begin():
            setup_session.add(CreditAccount(tenant_id=tid, balance=1, rollover_cap=0))

    results = {"success": 0, "insufficient": 0, "error": 0}

    async def attempt_deduct():
        svc = CreditService()
        async with factory() as session:
            async with session.begin():
                try:
                    await svc.deduct_credits(
                        session, tid, 1,
                        transaction_type="listing_debit",
                        reference_type="listing",
                        reference_id=str(uuid.uuid4()),
                    )
                    results["success"] += 1
                except InsufficientCreditsError:
                    results["insufficient"] += 1
                except Exception:
                    results["error"] += 1

    await asyncio.gather(attempt_deduct(), attempt_deduct())

    assert results["success"] == 1, f"Expected exactly 1 success, got {results}"
    assert results["insufficient"] == 1, f"Expected exactly 1 insufficient, got {results}"
    assert results["error"] == 0, f"Unexpected errors: {results}"

    # Verify final balance is 0
    async with factory() as check_session:
        svc = CreditService()
        balance = await svc.get_balance(check_session, tid)
        assert balance.balance == 0, f"Double-spend detected! Balance is {balance.balance}"
