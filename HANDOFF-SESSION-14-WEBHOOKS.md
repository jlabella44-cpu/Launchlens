# Session 14: Webhook Expansion — Credit Bundle Fulfillment, Renewal Grants, Payment Failures

## Context
The billing webhook (`src/launchlens/api/billing.py`) handles subscription events but doesn't process credit bundle purchases or grant credits on renewal. CreditService exists but the webhook doesn't call it. This is the critical glue between Stripe payments and the credit system.

## Tasks

### 1. Credit bundle checkout fulfillment
**File:** `src/launchlens/api/billing.py`

In `checkout.session.completed` handler, detect credit bundles via metadata:
```python
metadata = data_object.get("metadata", {})
if metadata.get("type") == "credit_bundle":
    bundle_size = int(metadata["bundle_size"])
    tenant_id = uuid.UUID(metadata["tenant_id"])
    invoice_id = data_object.get("id", "")

    credit_svc = CreditService()
    await credit_svc.ensure_account(db, tenant_id)
    await credit_svc.add_credits(
        db, tenant_id, bundle_size,
        transaction_type="purchase",
        reference_type="stripe_invoice",
        reference_id=invoice_id,
        description=f"Credit bundle: {bundle_size} credits",
    )
    await db.commit()
    return {"status": "credits_granted", "amount": bundle_size}
```

### 2. Subscription renewal credit grants
In `invoice.paid` handler, grant included credits + process rollover:
```python
tenant = await db.get(Tenant, tenant_id)
if tenant and tenant.billing_model == "credit" and tenant.included_credits > 0:
    credit_svc = CreditService()
    await credit_svc.process_period_renewal(
        db, tenant_id, tenant.included_credits,
    )
    await db.commit()
```

### 3. Subscription cancellation
In `customer.subscription.deleted`:
```python
tenant.plan_tier = "lite"
tenant.included_credits = 0
# DON'T zero credit balance — purchased credits are theirs
```

### 4. Plan upgrade/downgrade
In `customer.subscription.updated`:
- Resolve new `plan_tier` from price_id
- Update `included_credits` and `rollover_cap` for new tier
- Use the TIER_DEFAULTS mapping

### 5. Failed payment handling
In `invoice.payment_failed`:
- Emit `billing.payment_failed` audit event
- Send failure notification email via email service
- After 3 consecutive failures: consider auto-downgrade to Lite

### 6. Idempotency
Every credit operation MUST use the Stripe event/invoice ID as `reference_id`. CreditService already checks for duplicate `reference_id` — ensure all webhook calls pass it.

### 7. Add new config for tier pricing
**File:** `src/launchlens/config.py`

Already has `stripe_price_lite`, `stripe_price_active_agent`, etc. Build a `TIER_FROM_PRICE` mapping:
```python
def resolve_tier(price_id: str) -> str:
    mapping = {
        settings.stripe_price_lite: "lite",
        settings.stripe_price_active_agent: "active_agent",
        settings.stripe_price_team: "team",
        settings.stripe_price_annual: "annual",
    }
    return mapping.get(price_id, "lite")
```

## Key files
- `src/launchlens/api/billing.py` — webhook handler (modify)
- `src/launchlens/services/credits.py` — CreditService (use, don't modify)
- `src/launchlens/services/billing.py` — BillingService (may need `resolve_tier()`)
- `src/launchlens/config.py` — Stripe price settings (already added)

## Verification
- Stripe test clock: complete credit bundle checkout → credits in balance
- Stripe test clock: subscription renewal → rollover + grant processed
- Cancel subscription → tier = lite, credits preserved
- Replay webhook → no duplicate credits
