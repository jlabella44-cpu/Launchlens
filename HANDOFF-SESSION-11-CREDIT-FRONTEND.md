# Session 11: Credit Frontend Integration — Billing Page, Listing Dialog, Plan Context

## Context
The credit system backend is on master (PR #22). Models, CreditService, and API endpoints (`/credits/*`, `/addons/*`) are live. Frontend has the types and API client methods but **no page uses them yet**. The billing page still shows old plan-based UI, listing creation doesn't show credit costs, and PlanContext doesn't expose credit balance.

## Tasks

### 1. Update PlanContext for dual-mode billing
**File:** `frontend/src/contexts/plan-context.tsx`

Currently exposes `plan`, `limits`, `isFeatureGated`. Add:
```typescript
billingModel: 'legacy' | 'credit'
creditBalance: number | null
canAffordListing: boolean
listingCreditCost: number
refreshCredits: () => Promise<void>
```

Fetch `GET /credits/balance` when `billingModel === 'credit'`. Refresh after listing creation or credit purchase.

### 2. Update billing page
**File:** `frontend/src/app/billing/page.tsx`

When `billing_model === 'credit'`:
- Credit balance display: large number, top of page
- "Buy Credits" button → credit bundle selection → Stripe checkout via `apiClient.purchaseCredits()`
- Credit transaction history table (call `apiClient.getCreditTransactions()`)
- Rollover indicator: "X credits roll over at period end (cap: Y)"
- Current tier name (Lite/Active Agent/Team)
- Keep invoice section below

### 3. Update listing creation dialog
**File:** `frontend/src/components/listings/create-listing-dialog.tsx`

When `billing_model === 'credit'`:
- Show credit cost: "This listing uses 1 credit. Balance: 8"
- Add-on checkboxes: AI Video Tour (+1), 3D Floorplan (+1), Social Pack (+1)
- Total cost summary: "Total: 3 credits"
- Insufficient credits: gray out submit, show "Buy Credits" link
- After listing created, call `POST /listings/{id}/addons` for each selected add-on
- Call `refreshCredits()` from PlanContext after creation

### 4. Update listing detail for add-ons
**File:** `frontend/src/app/listings/[id]/page.tsx`

- Show activated add-ons as badges near header
- For NEW/UPLOADING listings: "Add/Remove Add-ons" section
- Cancel listing button for credit users: calls `POST /listings/{id}/cancel`
- Show "Credits refunded" toast on cancel

### 5. Update PlanBadge
**File:** `frontend/src/components/ui/plan-badge.tsx`

For credit users: show "Add for 1 credit" instead of "Upgrade to Pro" lock icon.

## Key API Methods (already in api-client.ts)
```typescript
getCreditBalance(), getCreditTransactions(), purchaseCredits(),
getCreditPricing(), getAddons(), activateAddon(), getListingAddons(),
removeAddon(), cancelListing()
```

## Verification
- Credit user billing page → shows balance + transactions + buy button
- Create listing → credit cost preview → balance decrements
- Add-ons selected → total cost shown → addons activate after creation
- Cancel listing → credits refunded, toast shown
