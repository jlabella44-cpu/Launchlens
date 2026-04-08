# Phase 4: Social Direct Publish + Scheduling — Design Spec

> **Version:** 1.0 | **Date:** 2026-04-08 | **Status:** Active
> **Depends on:** Phase 2 (social features), Phase 3 (health score)

---

## 1. Overview

Phase 4 adds direct publishing and scheduling to the Social Post Hub. Users connect their Instagram, Facebook, and TikTok accounts via OAuth, then publish or schedule posts directly from the listing detail page — no copy-paste, no switching tabs.

Builds on Phase 2's foundation: `SocialAccount` model, `ListingEvent` tracking, `SocialPostHub` UI, `post_time_config` best-time windows, and `SocialReminderService`.

---

## 2. Goals

1. One-click publish from Social Post Hub to connected platforms.
2. Schedule posts at optimal times (pre-populated from best-time config).
3. Track publish status per platform with post URLs and error handling.
4. OAuth connect/disconnect for Instagram, Facebook, TikTok.
5. Plan-gated: publish requires Active Agent+, scheduling requires Team+.

### Non-Goals

- Auto-publish without user confirmation (legal/brand risk).
- Platform analytics ingestion (impressions, engagement) — Phase 5.
- Cross-posting optimization (same content adapted per platform) — future.

---

## 3. Data Model

### `scheduled_posts` table (new)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | RLS-scoped |
| `listing_id` | UUID FK | |
| `listing_event_id` | UUID FK | Which event triggered this post |
| `platform` | String(20) | instagram, facebook, tiktok |
| `caption` | Text | Post caption |
| `hashtags` | JSONB | Hashtag list |
| `media_s3_keys` | JSONB | S3 keys for photos/video to publish |
| `scheduled_at` | DateTime(tz) | When to publish (null = publish now) |
| `status` | String(20) | draft, scheduled, publishing, published, failed, cancelled |
| `platform_post_id` | String(255) | ID returned by platform after publish |
| `platform_post_url` | String(500) | Direct link to the published post |
| `published_at` | DateTime(tz) | When actually published |
| `error_message` | Text | Error details if failed |
| `retry_count` | Integer | Number of retry attempts |
| `created_at` | DateTime(tz) | |

### Extend `social_accounts` table

| Column | Type | Description |
|--------|------|-------------|
| `refresh_token_encrypted` | String(500) | OAuth refresh token |
| `scopes` | JSONB | Granted OAuth scopes |
| `page_id` | String(255) | Facebook Page ID / IG Business Account ID |
| `page_name` | String(255) | Display name of connected page |

---

## 4. OAuth Flows

### Instagram (via Meta Business API)
1. User clicks "Connect Instagram" → redirect to Meta OAuth
2. Callback receives auth code → exchange for access token + page token
3. List user's Instagram Business Accounts → store selected account
4. Token refresh via long-lived token exchange

### Facebook (via Meta Graph API)
1. Same Meta OAuth flow but requesting `pages_manage_posts` scope
2. Store Page access token (long-lived, ~60 days)
3. Publish via `/{page_id}/photos` or `/{page_id}/videos`

### TikTok (via TikTok for Business API)
1. Redirect to TikTok OAuth → callback with auth code
2. Exchange for access + refresh tokens
3. Publish via Content Posting API (video upload + publish)

### Token Management
- Tokens stored encrypted in `social_accounts.access_token_encrypted`
- Refresh tokens in `refresh_token_encrypted`
- Background check refreshes tokens within 24h of expiry
- Expired/revoked tokens set `status = "expired"` and notify user

---

## 5. Platform Publishers

Abstract `SocialPublisher` with platform-specific implementations:

```python
class SocialPublisher(ABC):
    async def publish(self, account: SocialAccount, post: ScheduledPost) -> PublishResult
    async def validate_token(self, account: SocialAccount) -> bool
```

Each publisher:
1. Downloads media from S3 (presigned URL or direct fetch)
2. Uploads to platform's media endpoint
3. Creates the post with caption + hashtags
4. Returns `PublishResult(platform_post_id, platform_post_url)`

Mock publisher available for testing (`USE_MOCK_PROVIDERS=true`).

---

## 6. API Endpoints

### OAuth
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/social-accounts/{platform}/connect` | User | Initiate OAuth redirect |
| GET | `/social-accounts/{platform}/callback` | Public | OAuth callback handler |

### Publishing
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/listings/{id}/social/publish` | User | Publish now to a platform |
| POST | `/listings/{id}/social/schedule` | User | Schedule a future post |
| GET | `/listings/{id}/social/posts` | User | List all posts (scheduled + published) |
| PATCH | `/social/posts/{id}/cancel` | User | Cancel a scheduled post |
| POST | `/social/posts/{id}/retry` | User | Retry a failed post |

### Publish Request Body
```json
{
  "platform": "instagram",
  "caption": "Just listed! 🏡 ...",
  "hashtags": ["justlisted", "realestate"],
  "media_s3_keys": ["listings/abc/hero.jpg"],
  "scheduled_at": null
}
```

### Schedule Request Body
Same as publish, but `scheduled_at` is a future ISO datetime.

---

## 7. Background Executor

`ScheduledPostExecutor` — runs alongside `OutboxPoller` and `IdxFeedPoller` in FastAPI lifespan.

Poll loop (every 60s):
1. Query `scheduled_posts WHERE status = 'scheduled' AND scheduled_at <= now()`
2. For each due post:
   a. Set `status = 'publishing'`
   b. Look up `SocialAccount` for the platform
   c. Call the platform publisher
   d. On success: set `status = 'published'`, store `platform_post_id`, `platform_post_url`, `published_at`
   e. On failure: increment `retry_count`, set `status = 'failed'` if `retry_count >= 3`, else reschedule +5min
3. Emit `social.post.published` or `social.post.failed` events via outbox

---

## 8. Plan Gating

| Feature | Free/Lite | Active Agent | Team |
|---------|-----------|-------------|------|
| Copy caption + download | Yes | Yes | Yes |
| Connect accounts (OAuth) | - | Yes | Yes |
| Publish now | - | 1 platform | All platforms |
| Schedule posts | - | - | Yes |
| Best-time suggestions | - | - | Yes |
| Retry failed posts | - | Yes | Yes |

---

## 9. Frontend Changes

### Connected Accounts (Settings)
- Replace username input with "Connect with Instagram/Facebook/TikTok" OAuth buttons
- Show connected status with page name + avatar
- Disconnect button revokes token

### Social Post Hub (Listing Detail)
- "Publish Now" button on each PlatformPostCard (replaces "Mark as posted" for connected accounts)
- "Schedule" button with datetime picker (pre-filled with next best-time window)
- Status badges: draft / scheduled / publishing / published / failed
- Published posts show link to view on platform
- Failed posts show error + "Retry" button

### Post Status Section
- Below platform cards: table/list of all scheduled + published posts
- Columns: platform, status, scheduled time, published time, link
- Cancel button for scheduled, retry for failed

---

## 10. Implementation Order

1. ScheduledPost model + SocialAccount extension + migration
2. OAuth service + connect/callback endpoints + config settings
3. Platform publishers (Instagram, Facebook, TikTok) + mock
4. Publish now + schedule API endpoints
5. ScheduledPostExecutor background task
6. Frontend: OAuth connect buttons, publish/schedule UI, status display
7. Plan gating in API + frontend
8. Tests
