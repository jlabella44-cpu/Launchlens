# Session 12: Credit System Tests — CreditService, Atomicity, Webhooks, Rollover

## Context
The credit system (models, CreditService, API endpoints) is on master with zero test coverage. CreditService uses `SELECT FOR UPDATE` for atomic deduction and has rollover, refund, and idempotency logic that all need tests.

## Tasks

### 1. CreditService unit tests
**New file:** `tests/test_services/test_credits.py`

```python
# Test cases:
test_deduct_credits_success          # balance decremented, transaction created
test_deduct_insufficient_credits     # raises InsufficientCreditsError
test_deduct_idempotency              # same reference_id twice → ValueError
test_add_credits                     # balance incremented, transaction created
test_add_credits_idempotency         # same reference_id twice → ValueError
test_refund_credits                  # finds original debit, creates positive txn
test_refund_no_original              # returns None when no debit found
test_ensure_account                  # creates if missing, returns existing
test_rollover_within_cap             # balance rolls up to cap
test_rollover_exceeds_cap            # excess expires, expiry txn created
test_rollover_with_grant             # new balance = rollover + included
```

Use the existing `db_session` fixture from `tests/conftest.py`. Create a `CreditAccount` in each test setup.

### 2. Concurrent deduction test
```python
async def test_concurrent_deductions():
    # Give tenant 1 credit
    # Launch two concurrent deduct_credits(1) calls via asyncio.gather
    # Exactly one should succeed, one should raise InsufficientCreditsError
    # Final balance must be 0
```

### 3. Credit API endpoint tests
**New file:** `tests/test_api/test_credits.py`

- `GET /credits/balance` → returns balance for authenticated user
- `GET /credits/transactions` → returns transaction history
- `GET /credits/pricing` → returns bundle list (no auth required)
- `POST /credits/purchase` → creates Stripe checkout session (mock stripe)

### 4. Addon API tests
**New file:** `tests/test_api/test_addons.py`

- `GET /addons` → catalog with 3 seeded add-ons
- `POST /listings/{id}/addons` → activates, deducts credit
- `POST /listings/{id}/addons` duplicate → 409
- `POST /listings/{id}/addons` insufficient → 402
- `DELETE /listings/{id}/addons/{slug}` → refunds if pre-pipeline
- `DELETE /listings/{id}/addons/{slug}` → 409 if pipeline running

### 5. Listing creation with credits
Extend `tests/test_api/test_listings.py`:
- `test_create_listing_credit_deduction` — credit deducted on creation
- `test_create_listing_insufficient_credits` — 402
- `test_create_listing_legacy_unchanged` — quota check for legacy tenant
- `test_cancel_listing_refunds` — cancel returns credits

### 6. Key files to reference
- `src/launchlens/services/credits.py` — CreditService implementation
- `src/launchlens/models/credit_account.py` — CreditAccount model
- `src/launchlens/models/credit_transaction.py` — CreditTransaction model
- `src/launchlens/api/credits.py` — credit endpoints
- `src/launchlens/api/addons.py` — addon endpoints
- `tests/conftest.py` — shared fixtures

## Verification
- `pytest tests/test_services/test_credits.py -v` — all pass
- `pytest tests/test_api/test_credits.py tests/test_api/test_addons.py -v` — all pass
- Concurrent test proves no double-spend
