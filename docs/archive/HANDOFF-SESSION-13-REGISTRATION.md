# Session 13: Registration Flow — Plan Selection, Credit Account, Onboarding

## Context
The pricing page links to `/register?plan=lite` etc, but the registration endpoint ignores the plan param. New users get `billing_model='credit'` and `plan_tier='lite'` by default, but no credit account is created and no onboarding flow guides them.

## Tasks

### 1. Handle plan_tier on registration
**File:** `src/launchlens/api/auth.py`

The `POST /register` endpoint creates a Tenant. Update to:
- Accept optional `plan_tier` field in request body
- Map tier → included_credits, rollover_cap, per_listing_credit_cost:
  ```python
  TIER_DEFAULTS = {
      'lite': {'included_credits': 0, 'rollover_cap': 5, 'per_listing_credit_cost': 1},
      'active_agent': {'included_credits': 1, 'rollover_cap': 3, 'per_listing_credit_cost': 1},
      'team': {'included_credits': 5, 'rollover_cap': 10, 'per_listing_credit_cost': 1},
  }
  ```
- Set `tenant.billing_model = 'credit'`, `tenant.plan_tier` from request
- Create `CreditAccount` with `balance = included_credits`, `rollover_cap` from tier
- If `included_credits > 0`, create a `plan_grant` CreditTransaction

**Schema update:** `src/launchlens/api/schemas/auth.py` — add `plan_tier: str = "lite"` to `RegisterRequest`

### 2. Update registration form
**File:** `frontend/src/app/register/page.tsx`

- Read `?plan=` from `useSearchParams()`
- Map URL param to tier: `lite`, `active_agent`, `team`, `annual`
- Show selected plan at top: "Signing up for Active Agent — $39/mo"
- If no plan param, show link: "Choose a plan first →" to `/pricing`
- Pass `plan_tier` in registration API call

### 3. Post-registration onboarding
**New file:** `frontend/src/app/onboarding/page.tsx`

After registration, redirect here. Three steps:
1. **Brand Kit** — "Set up your branding" → link to /settings (check if brand kit exists)
2. **First Listing** — "Upload your first listing" → link to /listings
3. **Buy Credits** — "Get credits to start" → credit purchase (only if balance = 0)

Track completed steps in `localStorage`. Show progress dots. Each step has "Skip" button. After all steps (or skip all), redirect to `/listings`.

### 4. Welcome email
**File:** `src/launchlens/api/auth.py`

After tenant + user created:
```python
from launchlens.services.email import get_email_service
email_svc = get_email_service()
await email_svc.send_template(user.email, "welcome", {
    "name": body.name, "plan_tier": tenant.plan_tier
})
```
Template `src/launchlens/templates/email/welcome.html` already exists.

### 5. Auth flow redirect
**File:** `frontend/src/app/auth-wrapper.tsx` or `login/page.tsx`

After login, check if onboarding was completed (localStorage flag). If not, redirect to `/onboarding`.

## Verification
- `/register?plan=active_agent` → form shows "Active Agent"
- Register → tenant has `billing_model=credit`, `plan_tier=active_agent`, credit account with 1 credit
- Redirect to `/onboarding` → 3-step flow
- Complete steps → redirect to `/listings`
- Welcome email received
