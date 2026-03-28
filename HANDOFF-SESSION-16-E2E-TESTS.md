# Session 16: End-to-End Integration Tests — Full Lifecycle Across All Modules

## Context
The system has 125+ Python files from 10+ merged PRs by parallel sessions. Individual components are tested but integration gaps likely exist — especially credit system + pipeline + addons + webhooks + dual billing. This session writes tests that cross module boundaries.

**Run this session LAST**, after #11-#15 are merged.

## Tasks

### 1. Full credit lifecycle test
**New file:** `tests/test_integration/test_credit_lifecycle.py`

```python
async def test_full_credit_journey():
    # 1. Register user → credit billing, plan_tier=active_agent, 1 credit
    # 2. Mock Stripe webhook: credit bundle purchase (5 credits) → balance: 6
    # 3. Create listing → 1 credit deducted → balance: 5
    # 4. Activate video addon → 1 credit deducted → balance: 4
    # 5. Upload assets, verify pipeline starts
    # 6. Verify pipeline runs video (addon enabled)
    # 7. Create second listing without addons → balance: 3
    # 8. Verify pipeline skips video
    # 9. Cancel third listing attempt → credit refunded
    # 10. Verify transaction ledger is consistent
```

### 2. Dual billing model coexistence
```python
async def test_legacy_and_credit_coexist():
    # Create legacy tenant (billing_model='legacy', plan='pro')
    # Create credit tenant (billing_model='credit', plan_tier='active_agent')
    # Both create listings
    # Legacy: quota check (no credits)
    # Credit: credit deduction (no quota check)
    # Both pipelines run with correct gating
```

### 3. Webhook idempotency stress
```python
async def test_webhook_idempotency():
    # Fire same checkout.session.completed 5 times
    # Credits granted exactly once
    # Fire same invoice.paid 3 times
    # Rollover processed exactly once
```

### 4. Pipeline failure + credit flow
```python
async def test_pipeline_failure_credit_flow():
    # Create listing (credit deducted)
    # Pipeline fails
    # Retry → no re-deduction
    # Cancel → credits refunded
    # Transaction ledger: debit + refund = net 0
```

### 5. API contract validation
**New file:** `tests/test_integration/test_api_contracts.py`

For critical endpoints, verify request/response shapes match frontend expectations:
- `POST /credits/purchase` → `{checkout_url: string}`
- `GET /credits/balance` → `{balance, rollover_balance, rollover_cap, period_start, period_end}`
- `POST /listings/{id}/addons` → `{id, addon_slug, addon_name, status, created_at}`
- `GET /billing/status` → includes `plan_tier`, `billing_model`, `credit_balance`

### 6. Cross-module smoke test
```python
async def test_full_system_smoke():
    # Register → login → create brand kit → create listing →
    # upload assets → pipeline runs → approve → export → download
    # Verify every state transition, every event emitted
```

## Key fixtures needed
- `credit_tenant` — tenant with billing_model='credit', credit account, 10 credits
- `legacy_tenant` — tenant with billing_model='legacy', plan='pro'
- Mock Stripe webhook helper
- Mock providers (vision, llm, video) that succeed

## Verification
- `pytest tests/test_integration/ -v` — all pass
- Run 3 times to confirm no flakiness
- Covers: registration → credits → listing → pipeline → delivery
