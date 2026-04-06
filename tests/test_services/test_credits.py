"""CreditService unit tests — FIFO deduction, dual-pool, rollover, idempotency."""
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.credit_account import CreditAccount
from listingjet.services.credits import CreditService, InsufficientCreditsError


async def _create_account(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    balance: int = 10,
    granted_balance: int | None = None,
    purchased_balance: int | None = None,
    rollover_cap: int = 5,
) -> CreditAccount:
    gb = granted_balance if granted_balance is not None else balance
    pb = purchased_balance if purchased_balance is not None else 0
    account = CreditAccount(
        tenant_id=tenant_id,
        balance=balance,
        granted_balance=gb,
        purchased_balance=pb,
        rollover_cap=rollover_cap,
    )
    session.add(account)
    await session.flush()
    return account


# --- deduct_credits ---


@pytest.mark.asyncio
async def test_deduct_credits_success(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=20, granted_balance=15, purchased_balance=5)
    svc = CreditService()

    txn = await svc.deduct_credits(
        db_session, tid, 3,
        transaction_type="listing_debit",
        reference_type="listing",
        reference_id=str(uuid.uuid4()),
    )

    assert txn.amount == -3
    assert txn.balance_after == 17
    balance = await svc.get_balance(db_session, tid)
    assert balance.balance == 17
    assert balance.granted_balance == 12  # FIFO: granted consumed first
    assert balance.purchased_balance == 5  # untouched


@pytest.mark.asyncio
async def test_deduct_fifo_spills_to_purchased(db_session: AsyncSession):
    """When granted credits are exhausted, remainder comes from purchased."""
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=15, granted_balance=5, purchased_balance=10)
    svc = CreditService()

    txn = await svc.deduct_credits(
        db_session, tid, 8,
        transaction_type="listing_debit",
        reference_type="listing",
        reference_id=str(uuid.uuid4()),
    )

    assert txn.amount == -8
    balance = await svc.get_balance(db_session, tid)
    assert balance.balance == 7
    assert balance.granted_balance == 0  # all 5 granted consumed
    assert balance.purchased_balance == 7  # 10 - 3 remaining


@pytest.mark.asyncio
async def test_deduct_insufficient_credits(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=2, granted_balance=2)
    svc = CreditService()

    with pytest.raises(InsufficientCreditsError, match="Need 5 credits, have 2"):
        await svc.deduct_credits(
            db_session, tid, 5,
            transaction_type="listing_debit",
            reference_type="listing",
            reference_id=str(uuid.uuid4()),
        )

    balance = await svc.get_balance(db_session, tid)
    assert balance.balance == 2


@pytest.mark.asyncio
async def test_deduct_idempotency(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=20, granted_balance=20)
    svc = CreditService()
    ref_id = str(uuid.uuid4())

    await svc.deduct_credits(
        db_session, tid, 3,
        transaction_type="listing_debit",
        reference_type="listing",
        reference_id=ref_id,
    )

    with pytest.raises(ValueError, match="Credits already deducted"):
        await svc.deduct_credits(
            db_session, tid, 3,
            transaction_type="listing_debit",
            reference_type="listing",
            reference_id=ref_id,
        )

    balance = await svc.get_balance(db_session, tid)
    assert balance.balance == 17


# --- add_credits ---


@pytest.mark.asyncio
async def test_add_credits_purchase_goes_to_purchased(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=5, granted_balance=5, purchased_balance=0)
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
    assert balance.granted_balance == 5  # untouched
    assert balance.purchased_balance == 10  # purchase goes to purchased pool


@pytest.mark.asyncio
async def test_add_credits_grant_goes_to_granted(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=5, granted_balance=5, purchased_balance=0)
    svc = CreditService()

    txn = await svc.add_credits(
        db_session, tid, 10,
        transaction_type="plan_grant",
        reference_type="stripe_invoice",
        reference_id=str(uuid.uuid4()),
        description="Monthly grant",
    )

    assert txn.amount == 10
    balance = await svc.get_balance(db_session, tid)
    assert balance.balance == 15
    assert balance.granted_balance == 15  # grant goes to granted pool
    assert balance.purchased_balance == 0


@pytest.mark.asyncio
async def test_add_credits_idempotency(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=5, granted_balance=5)
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
    assert balance.balance == 15


# --- refund_credits ---


@pytest.mark.asyncio
async def test_refund_credits(db_session: AsyncSession):
    tid = uuid.uuid4()
    listing_id = str(uuid.uuid4())
    await _create_account(db_session, tid, balance=20, granted_balance=20)
    svc = CreditService()

    await svc.deduct_credits(
        db_session, tid, 12,
        transaction_type="listing_debit",
        reference_type="listing",
        reference_id=listing_id,
    )
    assert (await svc.get_balance(db_session, tid)).balance == 8

    refund_txn = await svc.refund_credits(db_session, tid, listing_id)
    assert refund_txn is not None
    assert refund_txn.amount == 12
    assert refund_txn.transaction_type == "refund"
    balance = await svc.get_balance(db_session, tid)
    assert balance.balance == 20
    # Refunds go to purchased pool (they're "purchased-equivalent")
    assert balance.purchased_balance == 12


@pytest.mark.asyncio
async def test_refund_no_original(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=10, granted_balance=10)
    svc = CreditService()

    result = await svc.refund_credits(db_session, tid, str(uuid.uuid4()))
    assert result is None


# --- ensure_account ---


@pytest.mark.asyncio
async def test_ensure_account_creates_new(db_session: AsyncSession):
    tid = uuid.uuid4()
    svc = CreditService()

    account = await svc.ensure_account(db_session, tid, rollover_cap=15)
    assert account.tenant_id == tid
    assert account.balance == 0
    assert account.granted_balance == 0
    assert account.purchased_balance == 0
    assert account.rollover_cap == 15


@pytest.mark.asyncio
async def test_ensure_account_returns_existing(db_session: AsyncSession):
    tid = uuid.uuid4()
    existing = await _create_account(db_session, tid, balance=42, granted_balance=30, purchased_balance=12)
    svc = CreditService()

    account = await svc.ensure_account(db_session, tid)
    assert account.id == existing.id
    assert account.balance == 42


# --- rollover ---


@pytest.mark.asyncio
async def test_rollover_only_expires_granted(db_session: AsyncSession):
    """Rollover should only expire granted credits, never purchased."""
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=30, granted_balance=20, purchased_balance=10, rollover_cap=5)
    svc = CreditService()

    await svc.process_period_renewal(db_session, tid, included_credits=25)

    balance = await svc.get_balance(db_session, tid)
    # granted: 20 -> capped to 5 (15 expired) -> 5 + 25 new = 30
    # purchased: 10 (untouched)
    # total: 30 + 10 = 40
    assert balance.granted_balance == 30
    assert balance.purchased_balance == 10
    assert balance.balance == 40
    assert balance.rollover_balance == 5

    txns = await svc.get_transactions(db_session, tid)
    expiry_txns = [t for t in txns if t.transaction_type == "expiry"]
    assert len(expiry_txns) == 1
    assert expiry_txns[0].amount == -15


@pytest.mark.asyncio
async def test_rollover_within_cap(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=3, granted_balance=3, purchased_balance=0, rollover_cap=5)
    svc = CreditService()

    await svc.process_period_renewal(db_session, tid, included_credits=10)

    balance = await svc.get_balance(db_session, tid)
    # 3 rolls over (under cap of 5) + 10 new = 13
    assert balance.balance == 13
    assert balance.granted_balance == 13
    assert balance.rollover_balance == 3


@pytest.mark.asyncio
async def test_rollover_exceeds_cap(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=8, granted_balance=8, purchased_balance=0, rollover_cap=5)
    svc = CreditService()

    await svc.process_period_renewal(db_session, tid, included_credits=10)

    balance = await svc.get_balance(db_session, tid)
    # 5 rolls over (capped) + 10 new = 15. 3 expired.
    assert balance.balance == 15
    assert balance.granted_balance == 15
    assert balance.rollover_balance == 5

    txns = await svc.get_transactions(db_session, tid)
    expiry_txns = [t for t in txns if t.transaction_type == "expiry"]
    assert len(expiry_txns) == 1
    assert expiry_txns[0].amount == -3


@pytest.mark.asyncio
async def test_rollover_with_grant(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=2, granted_balance=2, purchased_balance=0, rollover_cap=5)
    svc = CreditService()

    await svc.process_period_renewal(db_session, tid, included_credits=5)

    balance = await svc.get_balance(db_session, tid)
    assert balance.balance == 7

    txns = await svc.get_transactions(db_session, tid)
    grant_txns = [t for t in txns if t.transaction_type == "plan_grant"]
    assert len(grant_txns) == 1
    assert grant_txns[0].amount == 5


# --- get_transactions ---


@pytest.mark.asyncio
async def test_get_transactions_ordered(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=20, granted_balance=20)
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


# --- deduct_credits error: insufficient raises and balance unchanged ---


@pytest.mark.asyncio
async def test_deduct_credits_insufficient_raises_error(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=2, granted_balance=2)
    svc = CreditService()

    with pytest.raises(InsufficientCreditsError):
        await svc.deduct_credits(
            db_session, tid, 5,
            transaction_type="listing_debit",
            reference_type="listing",
            reference_id=str(uuid.uuid4()),
        )

    balance = await svc.get_balance(db_session, tid)
    assert balance.balance == 2


# --- refund with no matching transaction ---


@pytest.mark.asyncio
async def test_refund_credits_no_matching_transaction(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=10, granted_balance=10)
    svc = CreditService()

    result = await svc.refund_credits(db_session, tid, str(uuid.uuid4()))
    assert result is None


# --- period renewal respects rollover cap ---


@pytest.mark.asyncio
async def test_period_renewal_respects_rollover_cap(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=8, granted_balance=8, purchased_balance=0, rollover_cap=5)
    svc = CreditService()

    await svc.process_period_renewal(db_session, tid, included_credits=3)

    balance = await svc.get_balance(db_session, tid)
    assert balance.balance == 8
    assert balance.rollover_balance == 5

    txns = await svc.get_transactions(db_session, tid)
    expiry_txns = [t for t in txns if t.transaction_type == "expiry"]
    assert len(expiry_txns) == 1
    assert expiry_txns[0].amount == -3

    grant_txns = [t for t in txns if t.transaction_type == "plan_grant"]
    assert len(grant_txns) == 1
    assert grant_txns[0].amount == 3


# --- add_credits creates transaction record ---


@pytest.mark.asyncio
async def test_add_credits_creates_transaction_record(db_session: AsyncSession):
    tid = uuid.uuid4()
    await _create_account(db_session, tid, balance=5, granted_balance=5)
    svc = CreditService()

    txn = await svc.add_credits(
        db_session, tid, 10,
        transaction_type="purchase",
        reference_type="stripe_invoice",
        reference_id=str(uuid.uuid4()),
        description="10 credit bundle",
    )

    assert txn.amount == 10
    assert txn.transaction_type == "purchase"
    assert txn.balance_after == 15

    txns = await svc.get_transactions(db_session, tid)
    assert len(txns) == 1
    assert txns[0].amount == 10
    assert txns[0].balance_after == 15
    assert txns[0].transaction_type == "purchase"


# --- concurrent deduction (5 concurrent from 36 credits) ---


@pytest.mark.asyncio
async def test_deduct_credits_concurrent_no_overdraw(test_engine):
    """Set up tenant with 36 credits (3 listings worth at 12cr each),
    fire 5 concurrent deduct(12) calls. Exactly 3 succeed, 2 fail, final balance is 0."""
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    tid = uuid.uuid4()

    async with factory() as setup_session:
        async with setup_session.begin():
            setup_session.add(CreditAccount(
                tenant_id=tid, balance=36, granted_balance=36, purchased_balance=0, rollover_cap=0,
            ))

    results = {"success": 0, "insufficient": 0, "error": 0}

    async def attempt_deduct():
        svc = CreditService()
        async with factory() as session:
            async with session.begin():
                try:
                    await svc.deduct_credits(
                        session, tid, 12,
                        transaction_type="listing_debit",
                        reference_type="listing",
                        reference_id=str(uuid.uuid4()),
                    )
                    results["success"] += 1
                except InsufficientCreditsError:
                    results["insufficient"] += 1
                except Exception:
                    results["error"] += 1

    await asyncio.gather(*[attempt_deduct() for _ in range(5)])

    assert results["success"] == 3, f"Expected 3 successes, got {results}"
    assert results["insufficient"] == 2, f"Expected 2 failures, got {results}"
    assert results["error"] == 0, f"Unexpected errors: {results}"

    async with factory() as check_session:
        svc = CreditService()
        balance = await svc.get_balance(check_session, tid)
        assert balance.balance == 0, f"Overdraw detected! Balance is {balance.balance}"


# --- original concurrent deduction test (2 from 12 credits) ---


@pytest.mark.asyncio
async def test_concurrent_deductions_no_double_spend(test_engine):
    """Two simultaneous deductions of 12 credits from a 12-credit account:
    one should succeed, one should raise InsufficientCreditsError."""
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    tid = uuid.uuid4()

    async with factory() as setup_session:
        async with setup_session.begin():
            setup_session.add(CreditAccount(
                tenant_id=tid, balance=12, granted_balance=12, purchased_balance=0, rollover_cap=0,
            ))

    results = {"success": 0, "insufficient": 0, "error": 0}

    async def attempt_deduct():
        svc = CreditService()
        async with factory() as session:
            async with session.begin():
                try:
                    await svc.deduct_credits(
                        session, tid, 12,
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

    async with factory() as check_session:
        svc = CreditService()
        balance = await svc.get_balance(check_session, tid)
        assert balance.balance == 0, f"Double-spend detected! Balance is {balance.balance}"
