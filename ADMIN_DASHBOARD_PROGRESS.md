# Admin Dashboard — Progress & Next Steps

## Completed

### 1. Backend Schemas (`src/listingjet/api/schemas/admin.py`)
- Added `AdminListingResponse` — listing with tenant_name for cross-tenant view
- Added `AdminUpdateListingRequest` — address/metadata/state edit
- Added `AuditLogResponse` — audit log entry with from_attributes
- Added `AdminUserResponse` — user with tenant_name
- Added `SystemEventResponse` — system event for health monitoring

### 2. Backend API Endpoints (`src/listingjet/api/admin.py`)
- `GET /admin/listings` — paginated, filterable listing of all listings (state, tenant_id, search, limit/offset)
- `PATCH /admin/listings/{listing_id}` — update address/metadata/state with audit trail
- `POST /admin/listings/{listing_id}/retry` — admin retry failed/timed-out listings (cross-tenant, triggers Temporal)
- `GET /admin/users` — cross-tenant user list with search/role/tenant filters
- `GET /admin/audit-log` — paginated audit log with action/resource_type/tenant filters
- `GET /admin/events/recent` — recent system events for health tab

### 3. Frontend Types (`frontend/src/lib/types.ts`)
- Added `AdminListingItem`, `AdminUserItem`, `AuditLogEntry`, `SystemEvent`, `RevenueBreakdownResponse`
- Extended `AdminTenantResponse` with `stripe_subscription_id`, `webhook_url`

### 4. Frontend API Client (`frontend/src/lib/api-client.ts`)
- `adminListings(params?)` — GET /admin/listings
- `adminRetryListing(listingId)` — POST /admin/listings/{id}/retry
- `adminUpdateListing(listingId, data)` — PATCH /admin/listings/{id}
- `adminAllUsers(params?)` — GET /admin/users
- `adminChangeUserRole(userId, role)` — PATCH /admin/users/{id}/role
- `adminInviteUser(tenantId, data)` — POST /admin/tenants/{id}/users
- `adminUpdateTenant(tenantId, data)` — PATCH /admin/tenants/{id}
- `adminTestWebhook(tenantId)` — POST /admin/tenants/{id}/test-webhook
- `adminAuditLog(params?)` — GET /admin/audit-log
- `adminRecentEvents(params?)` — GET /admin/events/recent
- `adminRevenue()` — GET /admin/analytics/revenue

### 5. Nav Update (`frontend/src/components/layout/nav.tsx`)
- Added conditional "Admin" link visible only when `user.role === "superadmin"`

---

## NOT YET DONE

### 6. Admin Page Rewrite (`frontend/src/app/admin/page.tsx`)
This is the big remaining piece. Rewrite the single-view page into a **tabbed layout** with 5 tabs:

#### Tab: Overview (default)
- Keep existing: platform stats grid (4 cards), global credit ledger
- ADD: Listings by State table from `stats.listings_by_state` (color-code failed/pipeline_timeout red)
- ADD: "Attention Required" alert — count of failed + pipeline_timeout, clickable to jump to Listings tab filtered
- ADD: Revenue summary from `adminRevenue()`
- ADD: Recent events feed from `adminRecentEvents({ limit: 10 })`

#### Tab: Tenants
- Existing tenant roster table (search + sort)
- Click tenant → detail panel with:
  - Edit form (name, plan dropdown, webhook_url) → `adminUpdateTenant()`
  - "Test Webhook" button → `adminTestWebhook()`
  - User sub-table → `adminTenantUsers()` (existing backend, use `adminAllUsers({ tenant_id })`)
  - Role change dropdowns per user → `adminChangeUserRole()`
  - Invite user form (email, name, password, role) → `adminInviteUser()`
  - Credit section: balance, adjustment form, recent transactions (existing logic)

#### Tab: Listings
- Filters: state dropdown, tenant dropdown, address search
- Table: Address, Tenant, State (badge), Credit Cost, Updated, Actions
- State badge colors: red=failed/pipeline_timeout, green=delivered/tracking, amber=in-progress, gray=other
- Actions: "Retry" (failed/pipeline_timeout only), "Edit" (opens modal for address/metadata fields)
- Pagination: limit/offset with prev/next

#### Tab: Credits
- Global credit ledger (dark card)
- Tenant credit table sorted by balance
- Click tenant → adjustment form + transaction history

#### Tab: Audit Log
- Filters: action dropdown, resource_type dropdown, tenant dropdown
- Table: Timestamp, Action, Resource Type, Resource ID, Details (expandable JSON), Tenant
- Pagination with "Load More"

### 7. Lint & Verify
- `cd /home/user/Launchlens/src && python -m ruff check listingjet/api/admin.py listingjet/api/schemas/admin.py --fix`
- `cd /home/user/Launchlens/frontend && npx tsc --noEmit` (or `npx next build`)

### 8. Commit & Push
- Message: `"feat: full admin dashboard with listings, users, credits, and audit log"`
- Branch: `claude/frontend-polish-tier-config-7v5z3`

---

## Design Notes
- Single `"use client"` page with tab state, NOT separate routes
- Each tab is an inline function component (e.g. `function OverviewTab(...)`)
- Aviation theme: `bg-white rounded-2xl border-slate-100`, `text-[10px] uppercase tracking-wider`, `#F97316` orange accent
- Tab bar: horizontal pills with `bg-[#F97316] text-white` active, `bg-slate-100 text-slate-500` inactive
- Modals: simple overlay div with `fixed inset-0 bg-black/50` backdrop
- All data fetching via `apiClient.admin*()` methods in useEffect hooks
