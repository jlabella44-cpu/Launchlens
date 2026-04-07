# Phase 2: Social Features — Remind & Equip

**Date:** 2026-04-06
**Status:** Design approved, ready for implementation planning
**Depends on:** Phase 1 (creation wizard + pricing restructure)

## Overview

Add social posting reminders and a "ready-to-post" experience to ListingJet. When a listing lifecycle event occurs (Just Listed, Open House, Price Change, Sold/Pending), agents receive email + in-app notifications timed to optimal posting windows. Notifications link to a Social Post Hub with platform-specific preview cards (Instagram, Facebook, TikTok) showing captions, hashtags, and video ready to copy/download. Includes a Connected Accounts settings page (model + UI, OAuth stubbed) to prepare for future auto-posting in Phase 6.

## Decisions

- **Approach:** Hybrid — remind & equip now, auto-post later (Phase 6)
- **Platforms:** Instagram, Facebook, TikTok
- **Listing events:** Just Listed, Open House, Price Change, Sold/Pending
- **Best-time-to-post:** Static per-platform recommendations based on industry research
- **Reminders:** Email (SES) + in-app notifications, max 2 touches per event
- **Account linking:** Data model + settings UI now, OAuth stubbed for Phase 6

## Existing Infrastructure

Already built (from Phase 1 and earlier):
- `SocialContentAgent` generates captions for Instagram + Facebook (5 hook styles each, FHA-compliant)
- `SocialCutAgent` generates platform-optimized video cuts (IG Reels, TikTok, FB, YouTube Shorts)
- `social_contents` table stores captions per platform
- `VideoAsset.social_cuts` JSONB stores video cut metadata
- `social-preview.tsx` frontend component shows social cuts
- SES email service with template support
- Temporal workflow system for scheduling
- SSE event system for real-time updates

---

## Data Model

### New Tables

**`listing_events`** — Lifecycle events that trigger social content reminders

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `tenant_id` | UUID | FK, indexed |
| `listing_id` | UUID | FK, indexed |
| `event_type` | Enum | `just_listed`, `open_house`, `price_change`, `sold_pending` |
| `event_data` | JSONB | Event-specific data (e.g., `{"old_price": 500000, "new_price": 475000}`) |
| `notified_at` | Timestamp | Null until first reminder sent |
| `followup_sent_at` | Timestamp | Null until 24h follow-up sent |
| `posted_platforms` | JSONB | Array of platforms agent marked as posted, e.g. `["instagram", "facebook"]` |
| `created_at` | Timestamp | Server default |

**`social_accounts`** — Connected social accounts (stubbed for future OAuth)

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `tenant_id` | UUID | FK, indexed |
| `user_id` | UUID | FK |
| `platform` | Enum | `instagram`, `facebook`, `tiktok` |
| `platform_username` | String(100) | Manually entered handle |
| `platform_user_id` | String(255) | Nullable, populated when OAuth wired up |
| `access_token_encrypted` | String(500) | Nullable, future |
| `token_expires_at` | Timestamp | Nullable, future |
| `status` | String(20) | `pending`, `connected`, `disconnected` |
| `created_at` | Timestamp | Server default |

Unique constraint: `(user_id, platform)`

**`notifications`** — In-app notification system

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `tenant_id` | UUID | FK, indexed |
| `user_id` | UUID | FK, indexed |
| `type` | String(50) | e.g., `social_reminder`, `pipeline_complete` |
| `title` | String(255) | Notification title |
| `body` | String(1000) | Notification body text |
| `action_url` | String(500) | Deep link (e.g., `/listings/{id}/social?event={event_id}`) |
| `read_at` | Timestamp | Nullable, null = unread |
| `created_at` | Timestamp | Server default |

**No changes to existing tables.** Existing `social_contents` and `VideoAsset.social_cuts` already store generated content.

---

## Listing Event Detection

### Pipeline-Triggered Events

**`just_listed`** — Fires automatically when a listing reaches `DELIVERED` state. New activity `run_social_event` added at the end of the pipeline after `run_learning`:

```
... → learning → social_event (creates just_listed event)
```

### API-Triggered Events

**`open_house` and `sold_pending`** — Agent creates these explicitly:

```
POST /listings/{listing_id}/events
Body: { "event_type": "open_house", "event_data": { "date": "2026-04-15", "time": "2-4pm" } }
```

**`price_change`** — Detected automatically when `PATCH /listings/{id}` updates the price field. The endpoint compares old vs new price and creates a `listing_events` row if changed.

### Event → Notification Flow

1. Event created → insert `listing_events` row
2. Check best-time-to-post windows for each platform
3. If current time is within a posting window → send notification immediately
4. If not → schedule notification for next optimal window via Temporal delayed activity
5. If agent hasn't marked any platform as posted within 24 hours → one follow-up reminder
6. No further reminders after that (two touches max per event)

---

## Best-Time-to-Post Configuration

Static per-platform windows based on real estate industry research. Times are in the listing's local timezone (derived from listing address state → US timezone mapping).

```python
BEST_POST_TIMES = {
    "instagram": [
        {"days": ["tue", "wed", "thu"], "start": "10:00", "end": "13:00"},
        {"days": ["sat"], "start": "09:00", "end": "11:00"},
    ],
    "facebook": [
        {"days": ["tue", "wed", "thu"], "start": "09:00", "end": "12:00"},
        {"days": ["sat"], "start": "10:00", "end": "12:00"},
    ],
    "tiktok": [
        {"days": ["tue", "thu"], "start": "14:00", "end": "17:00"},
        {"days": ["fri", "sat"], "start": "19:00", "end": "21:00"},
    ],
}
```

**Timezone mapping:** Use listing address state to determine timezone. US-only for now:
- ET: Eastern states (NY, FL, GA, etc.)
- CT: Central states (TX, IL, etc.)
- MT: Mountain states (CO, AZ, etc.)
- PT: Pacific states (CA, WA, OR, etc.)

---

## Notification & Reminder Engine

### Email (SES)

Uses existing `EmailService.send_notification()` pattern.

**New template:** `social_reminder`
- Subject: "Time to share: {address} on social media"
- Body: Event context + platform recommendations + CTA button
- CTA links to: `/listings/{id}/social?event={event_id}`
- One email per event mentioning all three platforms

**Follow-up template:** `social_reminder_followup`
- Subject: "Reminder: Share {address} — best engagement window closing"
- Sent 24 hours after first notification if no platform marked as posted

### In-App Notifications

**Frontend:**
- Bell icon in nav bar with unread count badge
- Dropdown panel showing recent notifications
- Clicking notification navigates to action_url

**Polling:** `GET /notifications?unread=true` polled every 60 seconds (or piggyback on existing SSE if available)

### Notification API Endpoints

```
GET    /notifications              — List notifications (paginated, ?unread=true filter)
PATCH  /notifications/{id}/read    — Mark single notification as read
PATCH  /notifications/read-all     — Mark all notifications as read
```

---

## Social Post Hub (Frontend)

### Route

`/listings/{id}/social` — also accessible as a "Social" tab on the listing detail page.

### Layout

```
┌─────────────────────────────────────────────────────┐
│  ← Back to Listing                                  │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │ 🏠 Just Listed at 123 Main St               │    │
│  │    April 6, 2026                            │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ Instagram │  │ Facebook │  │ TikTok   │         │
│  │          │  │          │  │          │         │
│  │ [video]  │  │ [video]  │  │ [video]  │         │
│  │          │  │          │  │          │         │
│  │ Caption  │  │ Caption  │  │ Caption  │         │
│  │ hooks:   │  │ hooks:   │  │ (uses IG │         │
│  │ [tabs]   │  │ [tabs]   │  │ caption) │         │
│  │          │  │          │  │          │         │
│  │ #hashtags│  │          │  │ #hashtags│         │
│  │          │  │          │  │          │         │
│  │ [Copy]   │  │ [Copy]   │  │ [Copy]   │         │
│  │ [Download│  │ [Download│  │ [Download│         │
│  │  Video]  │  │  Video]  │  │  Video]  │         │
│  │          │  │          │  │          │         │
│  │ ☐ Posted │  │ ☐ Posted │  │ ☐ Posted │         │
│  └──────────┘  └──────────┘  └──────────┘         │
│                                                     │
│  Connected: @janedoe (IG) · Not connected (FB, TT) │
└─────────────────────────────────────────────────────┘
```

### Platform Card Features

- **Video preview:** Thumbnail from social cut with play button overlay. Clicking plays in a modal.
- **Caption hook selector:** Tabs for 5 styles (storyteller, data-driven, luxury_minimalist, urgency, lifestyle). Switching tabs updates the displayed caption. Selected hook persisted in localStorage.
- **Hashtags:** Shown below caption for Instagram and TikTok. Included in copy action.
- **Copy Caption button:** Copies caption + hashtags to clipboard. Toast confirmation.
- **Download Video button:** Direct download of the platform-specific social cut video file.
- **Mark as Posted checkbox:** Updates `listing_events.posted_platforms` via API. Shows check + timestamp when marked.

### TikTok Captions

TikTok captions are not currently generated by `SocialContentAgent` (only Instagram and Facebook). Two options:
- Reuse Instagram captions for TikTok (shorter, hashtag-heavy style works for both)
- Add TikTok as a third platform in `SocialContentAgent`

**Decision:** Reuse Instagram captions for TikTok. They're already short-form with hashtags, which matches TikTok's style. Add native TikTok caption generation later if agents request it.

### Listing Detail Integration

- New "Social" tab on the listing detail page
- Tab shows badge with count of unposted events
- Tab content embeds the Social Post Hub

### Navigation from Notifications

Email CTA and in-app notification both link to `/listings/{id}/social?event={event_id}`, which:
1. Opens the Social Post Hub
2. Scrolls to / highlights the specific event
3. Marks the notification as read

---

## Connected Accounts Settings

### Location

New section in the existing settings/account page.

### UI

"Connected Accounts" card with three rows (Instagram, Facebook, TikTok):
- Platform icon + name
- Username input field (text, prefixed with "@")
- Status badge: "Pending" (username entered), "Not Connected" (empty)
- Save button per row
- Note at bottom: "Auto-posting coming soon. For now, we'll personalize your social reminders."

### API Endpoints

```
GET    /social-accounts              — List connected accounts for current user
POST   /social-accounts              — Create/update account { platform, platform_username }
DELETE /social-accounts/{id}         — Remove a connected account
```

### Integration with Social Post Hub

If a `social_accounts` entry exists for a platform, the post hub card shows:
- "@username" badge on the platform card
- Slightly different CTA: "Copy & Post as @username"

If no entry: "Connect Account" link → navigates to settings page.

---

## Listing Events API

### Endpoints

```
POST   /listings/{listing_id}/events           — Create a listing event (open_house, sold_pending)
GET    /listings/{listing_id}/events            — List events for a listing
PATCH  /listings/{listing_id}/events/{id}/posted — Mark platform(s) as posted
```

### Event Creation Request

```json
{
    "event_type": "open_house",
    "event_data": {
        "date": "2026-04-15",
        "time": "2-4pm"
    }
}
```

Valid `event_type` values: `open_house`, `sold_pending`. (`just_listed` is pipeline-triggered only. `price_change` is auto-detected.)

### Mark as Posted Request

```json
{
    "platform": "instagram"
}
```

Appends the platform to `posted_platforms` JSONB array. Idempotent.

---

## Pipeline Changes

Add `run_social_event` activity at the end of the pipeline, after `run_learning`:

```
... → learning → social_event
```

The activity:
1. Creates a `listing_events` row with `event_type=just_listed`
2. Calls the notification service to schedule/send reminders
3. Non-blocking (pipeline still completes even if this fails)

---

## Key Files Reference

### Backend — New Files
- `src/listingjet/models/listing_event.py` — ListingEvent model
- `src/listingjet/models/social_account.py` — SocialAccount model
- `src/listingjet/models/notification.py` — Notification model
- `src/listingjet/api/listing_events.py` — Listing events router
- `src/listingjet/api/social_accounts.py` — Social accounts CRUD router
- `src/listingjet/api/notifications.py` — Notifications router
- `src/listingjet/services/social_reminder.py` — Reminder engine (best-time logic, email, notifications)
- `src/listingjet/services/post_time_config.py` — Static best-time-to-post configuration
- `src/listingjet/activities/social_event.py` — Pipeline activity for just_listed event
- `alembic/versions/040_social_features.py` — Migration for new tables

### Backend — Modified Files
- `src/listingjet/workflows/listing_pipeline.py` — Add social_event activity after learning
- `src/listingjet/api/listings_core.py` — Auto-detect price_change on PATCH
- `src/listingjet/main.py` — Register new routers

### Frontend — New Files
- `frontend/src/app/listings/[id]/social/page.tsx` — Social Post Hub route
- `frontend/src/components/listings/social-post-hub.tsx` — Post hub container
- `frontend/src/components/listings/platform-post-card.tsx` — Per-platform preview card
- `frontend/src/components/listings/caption-hook-selector.tsx` — Caption style tabs
- `frontend/src/components/notifications/notification-bell.tsx` — Nav bar bell icon + dropdown
- `frontend/src/components/settings/connected-accounts.tsx` — Settings section
- `frontend/src/lib/notifications.ts` — Notification polling hook

### Frontend — Modified Files
- `frontend/src/app/listings/[id]/page.tsx` — Add "Social" tab
- `frontend/src/components/layout/nav.tsx` — Add notification bell
- `frontend/src/app/settings/page.tsx` — Add connected accounts section
- `frontend/src/lib/api-client.ts` — Add event, notification, social account methods

---

## Verification Plan

1. Create listing → pipeline completes → `just_listed` event auto-created
2. Event triggers email + in-app notification at optimal posting window
3. Notification links to Social Post Hub with correct event context
4. Each platform card shows correct video cut + caption with hook tabs
5. Copy caption copies to clipboard including hashtags
6. Download video downloads the correct platform-specific cut
7. Mark as Posted updates `posted_platforms` and shows timestamp
8. 24h follow-up fires if no platform marked as posted
9. No third reminder after follow-up
10. Connected accounts CRUD works in settings
11. Social tab on listing detail shows badge for unposted events
12. Notification bell shows unread count, marks read on click
