# Listing-Level Permissions & Sharing — Feature Plan

> **Tier:** Highest plan only (Team/Enterprise)
> **Status:** Roadmap — not yet implemented
> **Dependencies:** Phase 3 team management (PR #95)

---

## 1. Overview

Allow agents, brokers, and team leads to share listings with specific people — within the same brokerage or across brokerages (co-listing). Supports granular permission levels, audit trails, and email notifications.

---

## 2. Permission Model

### 2.1 Sharing Granularity (Both Per-Listing and Per-Agent)

**Per-listing:** "Share this listing with Jordan" — grants access to one specific listing.

**Per-agent (blanket):** "Broker can see all of Agent X's listings" — a standing grant that applies to all current and future listings by that agent. Implemented as a `blanket_grant` on the agent's user_id rather than individual listings.

### 2.2 Permission Levels

| Level | Can View | Can Edit Photos/Description | Can Export Package | Can Publish to MLS | Can Manage Billing |
|-------|----------|----------------------------|--------------------|--------------------|-------------------|
| `read` | Yes | No | No | No | No |
| `write` | Yes | Yes | Yes | No | No |
| `publish` | Yes | Yes | Yes | **Yes** | No |
| `billing` | Yes | Yes | Yes | Yes | **Yes** |

**MLS Publishing Note:** The `publish` level is flagged for legal review. MLS rules may prohibit anyone other than the listing agent from publishing. Default to `write` for shared listings until legal clears `publish`. The UI should show a warning: _"MLS publishing by non-listing agents may violate MLS rules. Verify with your board."_

### 2.3 Broker Default Access

Brokers (admin role) within the same tenant get **automatic read access** to all listings in their brokerage. However, they must request or be granted `write` access to modify an agent's listing. This protects agent autonomy while giving brokers oversight.

Implementation: When querying listings, admins see all tenant listings in read-only mode. Write operations check for an explicit permission grant OR listing ownership.

---

## 3. Cross-Tenant Sharing (Co-Listing)

Real estate co-listing is common. An agent at Brokerage A can share a listing with an agent at Brokerage B.

### 3.1 How It Works

- The listing owner invites by email address
- If the email matches an existing ListingJet user (any tenant), they get access
- If the email doesn't match, an email invitation is sent with a link to register
- Cross-tenant shares are always **per-listing** (never blanket per-agent across tenants)
- Cross-tenant shares default to `write` level max — no `publish` or `billing` across tenants

### 3.2 Data Isolation

Cross-tenant shares only expose the shared listing, not any other tenant data. The shared user sees the listing in a "Shared With Me" section of their dashboard, separate from their own listings.

---

## 4. Data Model

### 4.1 New Table: `listing_permissions`

```sql
CREATE TABLE listing_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- What is being shared
    listing_id UUID REFERENCES listings(id) ON DELETE CASCADE,
    -- NULL listing_id + agent_user_id = blanket grant for all of that agent's listings
    agent_user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Who it's shared with
    grantee_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    grantee_tenant_id UUID NOT NULL REFERENCES tenants(id),
    
    -- Who granted it
    grantor_user_id UUID NOT NULL REFERENCES users(id),
    grantor_tenant_id UUID NOT NULL REFERENCES tenants(id),
    
    -- Permission level
    permission TEXT NOT NULL DEFAULT 'read'
        CHECK (permission IN ('read', 'write', 'publish', 'billing')),
    
    -- Expiration (optional)
    expires_at TIMESTAMPTZ,  -- NULL = permanent until revoked
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ,  -- soft-delete: NULL = active
    
    -- Constraints
    CONSTRAINT unique_active_permission 
        UNIQUE NULLS NOT DISTINCT (listing_id, agent_user_id, grantee_user_id, revoked_at)
);

CREATE INDEX idx_lp_listing ON listing_permissions(listing_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_lp_grantee ON listing_permissions(grantee_user_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_lp_agent ON listing_permissions(agent_user_id) WHERE revoked_at IS NULL;
```

**Row types:**
- `listing_id IS NOT NULL, agent_user_id IS NULL` → per-listing share
- `listing_id IS NULL, agent_user_id IS NOT NULL` → blanket per-agent share
- Both NULL is invalid (CHECK constraint)

### 4.2 New Table: `listing_audit_log`

```sql
CREATE TABLE listing_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    user_email TEXT NOT NULL,
    user_name TEXT,
    action TEXT NOT NULL,  -- 'edit_description', 'upload_photo', 'delete_photo', 'export', 'publish_mls', 'share', 'unshare'
    details JSONB DEFAULT '{}',  -- action-specific metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_listing ON listing_audit_log(listing_id, created_at DESC);
```

---

## 5. Expiration & Revocation

### 5.1 Approach: Optional Expiration + Manual Revoke

- **Default:** Permanent until manually revoked (most real estate workflows are ongoing relationships)
- **Optional expiration:** When sharing, the owner can set an expiry date (e.g., "until closing" or "30 days")
- **Auto-cleanup:** A daily cron job sets `revoked_at = now()` on expired permissions
- **Manual revoke:** Owner or admin can revoke at any time from the listing detail page or team settings
- **Revocation is soft-delete:** Sets `revoked_at` timestamp, preserving audit history

### 5.2 Why Not Always Time-Limited

Most broker-agent relationships are indefinite. Forcing expiration would create unnecessary friction (brokers re-granting access every month). Time limits are better as an opt-in for co-listing or temporary collaboration.

---

## 6. Notifications

### 6.1 Email Only (No Approval Flow)

When a listing is shared with someone, they receive an email:
- Subject: "[Agent Name] shared a listing with you on ListingJet"
- Body: listing address, thumbnail, permission level, link to view
- No accept/decline — access is immediate (the owner decided to share, that's the approval)

### 6.2 Notification Triggers

| Event | Recipient | Channel |
|-------|-----------|---------|
| Listing shared with you | Grantee | Email |
| Your access was revoked | Grantee | Email |
| Someone edited your shared listing | Listing owner | Email (digest, not per-edit) |
| Permission expiring in 3 days | Both parties | Email |

**Digest approach for edits:** Don't email on every save. Batch edit notifications into a daily digest: "3 changes were made to 742 Evergreen Terrace yesterday by Jordan Sterling."

---

## 7. API Endpoints

### 7.1 Permission Management

```
POST   /listings/{id}/permissions          — share a listing (owner or admin)
GET    /listings/{id}/permissions          — list who has access (owner or admin)
PATCH  /listings/{id}/permissions/{perm_id} — update permission level or expiry
DELETE /listings/{id}/permissions/{perm_id} — revoke access (soft-delete)
```

### 7.2 Blanket Grants (Per-Agent)

```
POST   /team/members/{user_id}/listing-access   — grant blanket access to all of user's listings
GET    /team/members/{user_id}/listing-access    — list blanket grants for a user
DELETE /team/members/{user_id}/listing-access/{perm_id} — revoke blanket grant
```

### 7.3 Shared With Me

```
GET    /listings/shared-with-me     — list all listings shared with current user
```

### 7.4 Audit Log

```
GET    /listings/{id}/audit-log     — get audit trail for a listing (owner, admin, or write+ access)
```

---

## 8. Frontend

### 8.1 Listing Detail Page — Share Button

- "Share" button in the listing header (only visible to owner + admin)
- Opens a panel/drawer with:
  - Email input to invite (autocomplete for team members)
  - Permission level dropdown (read/write/publish/billing)
  - Optional expiry date picker
  - List of current shares with role badges and revoke buttons

### 8.2 Dashboard — "Shared With Me" Section

- New tab or section on the listings dashboard
- Shows listings shared by others with a "Shared by [name]" badge
- Permission level indicator (read-only badge if no write access)
- Cross-tenant listings clearly labeled with brokerage name

### 8.3 Team Settings — Blanket Grants

- On the team management page, each member row gets a "Listing Access" dropdown:
  - "Own listings only" (default)
  - "Read all listings" (blanket read)
  - "Read/write all listings" (blanket write)
- Admins default to "Read all listings" (automatic, not stored as explicit grant)

### 8.4 Audit Log Viewer

- Tab on listing detail page: "Activity"
- Timeline view showing who did what and when
- Filterable by user and action type

---

## 9. Authorization Middleware

### 9.1 Permission Check Flow

For any listing operation:

```
1. Is user the listing owner? → Full access
2. Is user an admin in the listing's tenant? → Read access (write requires explicit grant)
3. Does user have an active per-listing permission? → Use that level
4. Does user have a blanket grant for the listing owner? → Use that level
5. None of the above → 403 Forbidden
```

### 9.2 Implementation

A FastAPI dependency `get_listing_permission(listing_id, user)` that returns the effective permission level. Used by all listing endpoints to gate operations.

---

## 10. Plan Gating

- Feature gated behind highest-tier plan
- Free/Lite/Active Agent plans: sharing UI is visible but locked with an upgrade prompt
- Team/Enterprise plan: full access
- Check `tenant.plan_tier` before allowing share operations
- Cross-tenant sharing requires BOTH tenants to be on the top tier

---

## 11. Legal / Compliance Flags

- [ ] **MLS publishing by non-listing agents:** Needs legal review before enabling `publish` level for shared users. Default to `write` max until cleared.
- [ ] **Data privacy:** Cross-tenant sharing exposes listing data (photos, address, description) to another brokerage. Terms of service should cover this.
- [ ] **GDPR/CCPA:** Audit log stores user email + name. Ensure deletion requests cascade to audit entries.

---

## 12. Implementation Phases

### Phase A: Core Permissions (1-2 sessions)
- `listing_permissions` table + migration
- Permission check middleware
- Per-listing share/revoke API endpoints
- Share panel UI on listing detail page

### Phase B: Blanket Grants + Dashboard (1 session)
- Blanket per-agent grants API
- "Shared With Me" dashboard section
- Team settings blanket access controls

### Phase C: Cross-Tenant Sharing (1 session)
- Email invitation flow for external users
- Cross-tenant permission constraints
- "Shared by [brokerage]" badges in UI

### Phase D: Audit Trail (1 session)
- `listing_audit_log` table + migration
- Audit logging middleware on all listing mutations
- Activity tab UI on listing detail page

### Phase E: Notifications (1 session)
- Email templates for share/revoke/expiry
- Daily edit digest job
- Notification preferences in user settings

### Phase F: Plan Gating + Polish (1 session)
- Tier check on share operations
- Upgrade prompts for lower-tier plans
- Edge cases, error handling, tests
