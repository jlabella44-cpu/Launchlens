# Session 15: Admin Dashboard — Credit Management, Revenue, Usage Analytics

## Context
Admins need visibility into credit usage across tenants. The admin endpoints show basic counts but nothing about credits, revenue breakdown, or usage patterns. The credit system is live — operators need tools to manage it.

## Tasks

### 1. Admin credit endpoints
**File:** `src/launchlens/api/admin.py`

Add:
```python
@router.get("/tenants/{tenant_id}/credits")
# Returns credit balance + last 50 transactions for a tenant

@router.post("/tenants/{tenant_id}/credits/adjust")
# Body: {"amount": 5, "reason": "Compensation for outage"}
# Creates admin_adjustment transaction, updates balance
# Emits audit event with admin user ID

@router.get("/credits/summary")
# Platform-wide: total outstanding, purchased/used/expired this month
```

### 2. Revenue analytics
**File:** `src/launchlens/api/analytics.py`

Add admin-only endpoints:
```python
@router.get("/admin/revenue")
# Breakdown: subscription revenue vs credit bundle revenue
# Query credit_transactions for 'purchase' type, sum amounts * price
# Query Stripe for subscription MRR

@router.get("/admin/usage-patterns")
# Listings per tenant per month distribution
# Credit purchase frequency
# Addon popularity (count by slug)
# Average credits per listing
```

### 3. Admin frontend page
**New file:** `frontend/src/app/admin/page.tsx`

Protected route (admin role only). Dashboard:
- Platform stats cards: tenants, users, listings, total credits outstanding
- Revenue section: subscription vs credit revenue (this month + trend)
- Tenant table: name, plan_tier, credit balance, listings this month (sortable)
- Click tenant → modal with credit transactions + "Adjust Credits" form

### 4. Credit adjustment audit trail
Every `admin_adjustment` transaction must include:
```python
metadata={"admin_user_id": str(current_user.id), "admin_email": current_user.email}
```
Plus emit_event with `event_type="admin.credit_adjustment"`.

### 5. Nav update for admin
Show "Admin" link in nav only for users with `role === 'admin'`.

## Verification
- Admin views `/admin` → sees platform stats + tenant table with credit balances
- Adjusts tenant credits → transaction created with audit trail
- Revenue breakdown shows correct numbers
