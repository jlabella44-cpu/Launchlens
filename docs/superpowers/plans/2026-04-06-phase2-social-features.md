# Phase 2: Social Features (Remind & Equip) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add listing event detection, social posting reminders (email + in-app), a Social Post Hub with platform preview cards, and a Connected Accounts settings page.

**Architecture:** Backend-first. New models for listing events, notifications, and social accounts. A reminder service applies best-time-to-post logic and dispatches emails + in-app notifications. A new pipeline activity creates `just_listed` events. Frontend adds a notification bell, Social Post Hub page, and Connected Accounts settings section.

**Tech Stack:** Python/FastAPI + SQLAlchemy + Alembic + Temporal (backend), SES email, Next.js 15 + React 19 + Tailwind v4 + Framer Motion (frontend)

---

## File Structure

### Backend — New Files
- `alembic/versions/040_social_features.py` — Migration: listing_events, social_accounts, notifications tables
- `src/listingjet/models/listing_event.py` — ListingEvent model
- `src/listingjet/models/social_account.py` — SocialAccount model
- `src/listingjet/models/notification.py` — Notification model
- `src/listingjet/services/post_time_config.py` — Static best-time-to-post windows + timezone mapping
- `src/listingjet/services/social_reminder.py` — Reminder engine: event → notification scheduling
- `src/listingjet/activities/social_event.py` — Pipeline activity for just_listed event creation
- `src/listingjet/api/listing_events.py` — Listing events router (CRUD + mark as posted)
- `src/listingjet/api/social_accounts.py` — Social accounts CRUD router
- `src/listingjet/api/notifications.py` — Notifications router (list, mark read)
- `src/listingjet/api/schemas/social.py` — Pydantic schemas for all three routers
- `src/listingjet/services/email_templates.py` — Add social_reminder + social_reminder_followup templates (modify existing)

### Backend — Modified Files
- `src/listingjet/models/__init__.py` — Register new models
- `src/listingjet/main.py` — Register new routers
- `src/listingjet/workflows/listing_pipeline.py` — Add social_event activity after learning
- `src/listingjet/activities/pipeline.py` — Import and register social_event activity
- `src/listingjet/api/listings_core.py` — Auto-detect price_change on PATCH

### Frontend — New Files
- `frontend/src/app/listings/[id]/social/page.tsx` — Social Post Hub route
- `frontend/src/components/listings/social-post-hub.tsx` — Post hub container
- `frontend/src/components/listings/platform-post-card.tsx` — Per-platform preview card
- `frontend/src/components/listings/caption-hook-selector.tsx` — Caption style tabs
- `frontend/src/components/notifications/notification-bell.tsx` — Nav bar bell + dropdown
- `frontend/src/hooks/use-notifications.ts` — Notification polling hook
- `frontend/src/components/settings/connected-accounts.tsx` — Connected accounts settings section

### Frontend — Modified Files
- `frontend/src/app/listings/[id]/page.tsx` — Add "Social" tab/section link
- `frontend/src/components/layout/nav.tsx` — Add notification bell
- `frontend/src/app/settings/page.tsx` — Add connected accounts section
- `frontend/src/lib/api-client.ts` — Add event, notification, social account methods

### Test Files
- `tests/test_models/test_listing_event.py`
- `tests/test_services/test_post_time_config.py`
- `tests/test_services/test_social_reminder.py`
- `tests/test_api/test_listing_events.py`
- `tests/test_api/test_notifications.py`
- `tests/test_api/test_social_accounts.py`

---

## Task 1: Database Migration — Social Features Tables

**Files:**
- Create: `alembic/versions/040_social_features.py`

- [ ] **Step 1: Create the migration**

```python
"""Social features: listing_events, social_accounts, notifications tables.

Revision ID: 040
Revises: 039
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "040"
down_revision = "039"


def upgrade():
    # listing_events table
    op.create_table(
        "listing_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("listing_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_data", JSONB, nullable=False, server_default="{}"),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("followup_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posted_platforms", JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # social_accounts table
    op.create_table(
        "social_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("platform_username", sa.String(100), nullable=False),
        sa.Column("platform_user_id", sa.String(255), nullable=True),
        sa.Column("access_token_encrypted", sa.String(500), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "platform", name="uq_social_accounts_user_platform"),
    )

    # notifications table
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.String(1000), nullable=False),
        sa.Column("action_url", sa.String(500), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_notifications_user_unread", "notifications", ["user_id", "read_at"])


def downgrade():
    op.drop_table("notifications")
    op.drop_table("social_accounts")
    op.drop_table("listing_events")
```

- [ ] **Step 2: Verify syntax**

Run: `cd C:/Users/Jeff/launchlens && python -c "import ast; ast.parse(open('alembic/versions/040_social_features.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add alembic/versions/040_social_features.py && git commit -m "feat: migration 040 — listing_events, social_accounts, notifications tables"
```

---

## Task 2: SQLAlchemy Models

**Files:**
- Create: `src/listingjet/models/listing_event.py`
- Create: `src/listingjet/models/social_account.py`
- Create: `src/listingjet/models/notification.py`
- Modify: `src/listingjet/models/__init__.py`

- [ ] **Step 1: Create ListingEvent model**

```python
# src/listingjet/models/listing_event.py
import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class ListingEvent(TenantScopedModel):
    __tablename__ = "listing_events"
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    followup_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_platforms: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
```

- [ ] **Step 2: Create SocialAccount model**

```python
# src/listingjet/models/social_account.py
import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from listingjet.database import Base


class SocialAccount(Base):
    __tablename__ = "social_accounts"
    __table_args__ = (UniqueConstraint("user_id", "platform", name="uq_social_accounts_user_platform"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    platform_username: Mapped[str] = mapped_column(String(100), nullable=False)
    platform_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_token_encrypted: Mapped[str | None] = mapped_column(String(500), nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 3: Create Notification model**

```python
# src/listingjet/models/notification.py
import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from listingjet.database import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_unread", "user_id", "read_at"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(String(1000), nullable=False)
    action_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 4: Register models in __init__.py**

Add to `src/listingjet/models/__init__.py`:

```python
from .listing_event import ListingEvent                      # noqa
from .social_account import SocialAccount                    # noqa
from .notification import Notification                       # noqa
```

- [ ] **Step 5: Verify imports**

Run: `cd C:/Users/Jeff/launchlens && python -c "from listingjet.models.listing_event import ListingEvent; from listingjet.models.social_account import SocialAccount; from listingjet.models.notification import Notification; print('Models OK')"`
Expected: `Models OK`

- [ ] **Step 6: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/models/listing_event.py src/listingjet/models/social_account.py src/listingjet/models/notification.py src/listingjet/models/__init__.py && git commit -m "feat: add ListingEvent, SocialAccount, Notification models"
```

---

## Task 3: Pydantic Schemas for Social APIs

**Files:**
- Create: `src/listingjet/api/schemas/social.py`

- [ ] **Step 1: Create all schemas**

```python
# src/listingjet/api/schemas/social.py
"""Schemas for social features: listing events, notifications, social accounts."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# --- Listing Events ---

class CreateListingEventRequest(BaseModel):
    event_type: str = Field(..., pattern="^(open_house|sold_pending)$")
    event_data: dict = Field(default_factory=dict)


class ListingEventResponse(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    event_type: str
    event_data: dict
    notified_at: datetime | None = None
    posted_platforms: list[str] = []
    created_at: datetime
    model_config = {"from_attributes": True}


class MarkPostedRequest(BaseModel):
    platform: str = Field(..., pattern="^(instagram|facebook|tiktok)$")


# --- Notifications ---

class NotificationResponse(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    body: str
    action_url: str | None = None
    read_at: datetime | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int


# --- Social Accounts ---

class CreateSocialAccountRequest(BaseModel):
    platform: str = Field(..., pattern="^(instagram|facebook|tiktok)$")
    platform_username: str = Field(..., min_length=1, max_length=100)


class SocialAccountResponse(BaseModel):
    id: uuid.UUID
    platform: str
    platform_username: str
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Verify import**

Run: `cd C:/Users/Jeff/launchlens && python -c "from listingjet.api.schemas.social import CreateListingEventRequest, NotificationResponse, SocialAccountResponse; print('Schemas OK')"`
Expected: `Schemas OK`

- [ ] **Step 3: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/api/schemas/social.py && git commit -m "feat: Pydantic schemas for listing events, notifications, social accounts"
```

---

## Task 4: Best-Time-to-Post Configuration

**Files:**
- Create: `src/listingjet/services/post_time_config.py`
- Create: `tests/test_services/test_post_time_config.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_services/test_post_time_config.py
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from listingjet.services.post_time_config import (
    BEST_POST_TIMES,
    get_listing_timezone,
    find_next_post_window,
)


def test_best_post_times_has_all_platforms():
    assert "instagram" in BEST_POST_TIMES
    assert "facebook" in BEST_POST_TIMES
    assert "tiktok" in BEST_POST_TIMES


def test_get_listing_timezone_east_coast():
    tz = get_listing_timezone("NY")
    assert tz == ZoneInfo("America/New_York")


def test_get_listing_timezone_west_coast():
    tz = get_listing_timezone("CA")
    assert tz == ZoneInfo("America/Los_Angeles")


def test_get_listing_timezone_central():
    tz = get_listing_timezone("TX")
    assert tz == ZoneInfo("America/Chicago")


def test_get_listing_timezone_mountain():
    tz = get_listing_timezone("CO")
    assert tz == ZoneInfo("America/Denver")


def test_get_listing_timezone_unknown_defaults_to_eastern():
    tz = get_listing_timezone("XX")
    assert tz == ZoneInfo("America/New_York")


def test_find_next_post_window_returns_datetime():
    # Tuesday 3am ET — should find a window later that day or same week
    now = datetime(2026, 4, 7, 3, 0, tzinfo=ZoneInfo("America/New_York"))  # Tuesday
    result = find_next_post_window("instagram", now)
    assert result is not None
    assert result > now


def test_find_next_post_window_during_window_returns_now():
    # Tuesday 11am ET — inside Instagram window (Tue 10am-1pm)
    now = datetime(2026, 4, 7, 11, 0, tzinfo=ZoneInfo("America/New_York"))  # Tuesday
    result = find_next_post_window("instagram", now)
    # Should return None (meaning "now is fine, post immediately")
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:/Users/Jeff/launchlens && python -m pytest tests/test_services/test_post_time_config.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Create post_time_config.py**

```python
# src/listingjet/services/post_time_config.py
"""Static best-time-to-post configuration and timezone mapping for social reminders."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

# Per-platform posting windows (day of week + time range, local time)
BEST_POST_TIMES: dict[str, list[dict]] = {
    "instagram": [
        {"days": ["tue", "wed", "thu"], "start": time(10, 0), "end": time(13, 0)},
        {"days": ["sat"], "start": time(9, 0), "end": time(11, 0)},
    ],
    "facebook": [
        {"days": ["tue", "wed", "thu"], "start": time(9, 0), "end": time(12, 0)},
        {"days": ["sat"], "start": time(10, 0), "end": time(12, 0)},
    ],
    "tiktok": [
        {"days": ["tue", "thu"], "start": time(14, 0), "end": time(17, 0)},
        {"days": ["fri", "sat"], "start": time(19, 0), "end": time(21, 0)},
    ],
}

_DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# US state -> timezone mapping
_STATE_TZ: dict[str, str] = {
    # Eastern
    **{s: "America/New_York" for s in [
        "CT", "DE", "FL", "GA", "IN", "KY", "ME", "MD", "MA", "MI",
        "NH", "NJ", "NY", "NC", "OH", "PA", "RI", "SC", "TN", "VT",
        "VA", "WV", "DC",
    ]},
    # Central
    **{s: "America/Chicago" for s in [
        "AL", "AR", "IL", "IA", "KS", "LA", "MN", "MS", "MO", "NE",
        "ND", "OK", "SD", "TX", "WI",
    ]},
    # Mountain
    **{s: "America/Denver" for s in [
        "AZ", "CO", "ID", "MT", "NM", "UT", "WY",
    ]},
    # Pacific
    **{s: "America/Los_Angeles" for s in [
        "CA", "NV", "OR", "WA",
    ]},
    # Other
    "AK": "America/Anchorage",
    "HI": "Pacific/Honolulu",
}


def get_listing_timezone(state_code: str) -> ZoneInfo:
    """Return timezone for a US state code. Defaults to Eastern if unknown."""
    tz_name = _STATE_TZ.get(state_code.upper(), "America/New_York")
    return ZoneInfo(tz_name)


def find_next_post_window(platform: str, now: datetime) -> datetime | None:
    """Find the next optimal posting window for a platform.

    Returns None if `now` is already inside a posting window (post immediately).
    Returns the start of the next window otherwise.
    """
    windows = BEST_POST_TIMES.get(platform, [])
    current_day = _DAY_NAMES[now.weekday()]
    current_time = now.time()

    # Check if we're currently in a window
    for window in windows:
        if current_day in window["days"] and window["start"] <= current_time < window["end"]:
            return None  # Post now

    # Find next upcoming window (search up to 7 days ahead)
    for days_ahead in range(0, 8):
        check_date = now + timedelta(days=days_ahead)
        check_day = _DAY_NAMES[check_date.weekday()]
        for window in windows:
            if check_day in window["days"]:
                window_start = check_date.replace(
                    hour=window["start"].hour,
                    minute=window["start"].minute,
                    second=0,
                    microsecond=0,
                )
                if window_start > now:
                    return window_start

    # Fallback: return tomorrow at 10am
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
```

- [ ] **Step 4: Run tests**

Run: `cd C:/Users/Jeff/launchlens && python -m pytest tests/test_services/test_post_time_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/services/post_time_config.py tests/test_services/test_post_time_config.py && git commit -m "feat: best-time-to-post config with timezone mapping"
```

---

## Task 5: Social Reminder Service

**Files:**
- Create: `src/listingjet/services/social_reminder.py`
- Create: `tests/test_services/test_social_reminder.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_services/test_social_reminder.py
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from listingjet.services.social_reminder import SocialReminderService


@pytest.fixture
def reminder_svc():
    return SocialReminderService()


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_create_notification(reminder_svc, mock_session):
    """Should create a notification record for a listing event."""
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    listing_id = uuid.uuid4()

    notif = await reminder_svc.create_notification(
        session=mock_session,
        user_id=user_id,
        tenant_id=tenant_id,
        listing_id=listing_id,
        event_type="just_listed",
        address="123 Main St",
    )
    mock_session.add.assert_called_once()
    assert notif.type == "social_reminder"
    assert "123 Main St" in notif.title


@pytest.mark.asyncio
async def test_should_send_followup_no_platforms_posted(reminder_svc):
    """Should send followup if no platforms posted after 24h."""
    event = MagicMock()
    event.posted_platforms = []
    event.notified_at = datetime(2026, 4, 6, 10, 0, tzinfo=ZoneInfo("America/New_York"))
    event.followup_sent_at = None
    now = datetime(2026, 4, 7, 11, 0, tzinfo=ZoneInfo("America/New_York"))  # 25h later
    assert reminder_svc.should_send_followup(event, now) is True


@pytest.mark.asyncio
async def test_should_not_send_followup_if_posted(reminder_svc):
    """Should NOT send followup if agent posted to at least one platform."""
    event = MagicMock()
    event.posted_platforms = ["instagram"]
    event.notified_at = datetime(2026, 4, 6, 10, 0, tzinfo=ZoneInfo("America/New_York"))
    event.followup_sent_at = None
    now = datetime(2026, 4, 7, 11, 0, tzinfo=ZoneInfo("America/New_York"))
    assert reminder_svc.should_send_followup(event, now) is False


@pytest.mark.asyncio
async def test_should_not_send_followup_twice(reminder_svc):
    """Should NOT send followup if already sent."""
    event = MagicMock()
    event.posted_platforms = []
    event.notified_at = datetime(2026, 4, 6, 10, 0, tzinfo=ZoneInfo("America/New_York"))
    event.followup_sent_at = datetime(2026, 4, 7, 10, 0, tzinfo=ZoneInfo("America/New_York"))
    now = datetime(2026, 4, 8, 10, 0, tzinfo=ZoneInfo("America/New_York"))
    assert reminder_svc.should_send_followup(event, now) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:/Users/Jeff/launchlens && python -m pytest tests/test_services/test_social_reminder.py -v`
Expected: FAIL

- [ ] **Step 3: Create social_reminder.py**

```python
# src/listingjet/services/social_reminder.py
"""Social reminder service — creates notifications and sends emails for listing events."""
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.notification import Notification

logger = logging.getLogger(__name__)

_FOLLOWUP_DELAY_HOURS = 24


class SocialReminderService:

    def create_notification(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        listing_id: uuid.UUID,
        event_type: str,
        address: str,
    ) -> Notification:
        """Create an in-app notification for a social reminder."""
        event_labels = {
            "just_listed": "Just Listed",
            "open_house": "Open House",
            "price_change": "Price Change",
            "sold_pending": "Sold/Pending",
        }
        label = event_labels.get(event_type, event_type)

        notif = Notification(
            tenant_id=tenant_id,
            user_id=user_id,
            type="social_reminder",
            title=f"{label}: {address}",
            body=f"Your listing at {address} is ready to share on social media. Best time to post is now!",
            action_url=f"/listings/{listing_id}/social",
        )
        session.add(notif)
        return notif

    async def send_email_reminder(
        self,
        to_email: str,
        listing_id: uuid.UUID,
        event_id: uuid.UUID,
        event_type: str,
        address: str,
        is_followup: bool = False,
    ) -> None:
        """Send email reminder via SES."""
        try:
            from listingjet.services.email import get_email_service
            email_svc = get_email_service()
            template = "social_reminder_followup" if is_followup else "social_reminder"
            email_svc.send_notification(
                to_email,
                template,
                address=address,
                event_type=event_type,
                listing_id=str(listing_id),
                event_id=str(event_id),
                social_url=f"https://app.listingjet.com/listings/{listing_id}/social?event={event_id}",
            )
        except Exception:
            logger.exception("social_reminder email failed for listing %s", listing_id)

    def should_send_followup(self, event, now: datetime) -> bool:
        """Check if a 24h follow-up reminder should be sent."""
        if event.followup_sent_at is not None:
            return False
        if len(event.posted_platforms) > 0:
            return False
        if event.notified_at is None:
            return False
        elapsed = now - event.notified_at
        return elapsed >= timedelta(hours=_FOLLOWUP_DELAY_HOURS)
```

- [ ] **Step 4: Run tests**

Run: `cd C:/Users/Jeff/launchlens && python -m pytest tests/test_services/test_social_reminder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/services/social_reminder.py tests/test_services/test_social_reminder.py && git commit -m "feat: social reminder service — notifications and email"
```

---

## Task 6: Email Templates for Social Reminders

**Files:**
- Modify: `src/listingjet/services/email_templates.py` (add new templates)

- [ ] **Step 1: Read the existing email_templates.py to understand the pattern**

Read `src/listingjet/services/email_templates.py` and find the `TEMPLATES` dict. Each template is a function that returns `(subject, html_body)`.

- [ ] **Step 2: Add social reminder templates**

Add two new template functions and register them in the `TEMPLATES` dict:

```python
def _social_reminder(**kwargs) -> tuple[str, str]:
    address = kwargs.get("address", "your listing")
    social_url = kwargs.get("social_url", "#")
    subject = f"Time to share: {address} on social media"
    html_body = f"""
    <h2>Your listing is ready to share!</h2>
    <p>Your listing at <strong>{address}</strong> has content ready for Instagram, Facebook, and TikTok.</p>
    <p>Now is a great time to post — your captions, hashtags, and video cuts are all prepared.</p>
    <p><a href="{social_url}" style="display:inline-block;padding:12px 24px;background:#4F46E5;color:white;text-decoration:none;border-radius:8px;">View & Post Now</a></p>
    <p style="color:#6B7280;font-size:14px;">Tip: Post during peak engagement hours for maximum visibility.</p>
    """
    return subject, html_body


def _social_reminder_followup(**kwargs) -> tuple[str, str]:
    address = kwargs.get("address", "your listing")
    social_url = kwargs.get("social_url", "#")
    subject = f"Reminder: Share {address} — engagement window closing"
    html_body = f"""
    <h2>Don't miss the engagement window</h2>
    <p>Your listing at <strong>{address}</strong> still hasn't been shared on social media.</p>
    <p>Listings shared within 48 hours of going live get significantly more engagement.</p>
    <p><a href="{social_url}" style="display:inline-block;padding:12px 24px;background:#4F46E5;color:white;text-decoration:none;border-radius:8px;">Share Now</a></p>
    """
    return subject, html_body
```

Add to the `TEMPLATES` dict:
```python
    "social_reminder": _social_reminder,
    "social_reminder_followup": _social_reminder_followup,
```

- [ ] **Step 3: Verify**

Run: `cd C:/Users/Jeff/launchlens && python -c "from listingjet.services.email_templates import TEMPLATES; assert 'social_reminder' in TEMPLATES; assert 'social_reminder_followup' in TEMPLATES; print('Templates OK')"`
Expected: `Templates OK`

- [ ] **Step 4: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/services/email_templates.py && git commit -m "feat: add social_reminder email templates"
```

---

## Task 7: Pipeline Activity — Social Event

**Files:**
- Create: `src/listingjet/activities/social_event.py`
- Modify: `src/listingjet/activities/pipeline.py`
- Modify: `src/listingjet/workflows/listing_pipeline.py`

- [ ] **Step 1: Create social_event activity**

```python
# src/listingjet/activities/social_event.py
"""Pipeline activity: create a just_listed event after pipeline completion."""
import logging

from temporalio import activity

from listingjet.agents.base import AgentContext

logger = logging.getLogger(__name__)


@activity.defn
async def run_social_event(context: AgentContext) -> dict:
    """Create a just_listed listing event and trigger social reminders."""
    from listingjet.database import get_async_session
    from listingjet.models.listing import Listing
    from listingjet.models.listing_event import ListingEvent
    from listingjet.models.user import User, UserRole
    from listingjet.services.post_time_config import find_next_post_window, get_listing_timezone
    from listingjet.services.social_reminder import SocialReminderService
    from sqlalchemy import select

    async with get_async_session() as session:
        listing = (await session.execute(
            select(Listing).where(Listing.id == context.listing_id)
        )).scalar_one_or_none()
        if not listing:
            return {"status": "listing_not_found"}

        # Check for duplicate event
        existing = (await session.execute(
            select(ListingEvent).where(
                ListingEvent.listing_id == listing.id,
                ListingEvent.event_type == "just_listed",
            ).limit(1)
        )).scalar_one_or_none()
        if existing:
            return {"status": "already_exists", "event_id": str(existing.id)}

        event = ListingEvent(
            tenant_id=listing.tenant_id,
            listing_id=listing.id,
            event_type="just_listed",
            event_data={},
        )
        session.add(event)
        await session.flush()

        # Find the tenant admin to notify
        admin = (await session.execute(
            select(User).where(
                User.tenant_id == listing.tenant_id,
                User.role == UserRole.ADMIN,
            ).limit(1)
        )).scalar_one_or_none()

        if admin:
            address = listing.address.get("street", "your listing")
            state_code = listing.address.get("state", "NY")
            tz = get_listing_timezone(state_code)

            from datetime import datetime
            now = datetime.now(tz)
            next_window = find_next_post_window("instagram", now)

            svc = SocialReminderService()
            if next_window is None:
                # Inside a posting window — notify now
                svc.create_notification(
                    session=session,
                    user_id=admin.id,
                    tenant_id=listing.tenant_id,
                    listing_id=listing.id,
                    event_type="just_listed",
                    address=address,
                )
                from datetime import timezone as tz_mod
                event.notified_at = datetime.now(tz_mod.utc)

                await svc.send_email_reminder(
                    to_email=admin.email,
                    listing_id=listing.id,
                    event_id=event.id,
                    event_type="just_listed",
                    address=address,
                )
            # If not in window, notification scheduling handled by a separate scheduled task

        await session.commit()
        return {"status": "created", "event_id": str(event.id)}
```

- [ ] **Step 2: Register activity in pipeline.py**

In `src/listingjet/activities/pipeline.py`, add the import and register:

```python
from listingjet.activities.social_event import run_social_event
```

Add `run_social_event` to the `ALL_ACTIVITIES` list at the bottom of the file.

- [ ] **Step 3: Add social_event to pipeline workflow**

In `src/listingjet/workflows/listing_pipeline.py`, add the import at the top (inside `with workflow.unsafe.imports_passed_through():`):

```python
from listingjet.activities.social_event import run_social_event
```

Add after the `run_learning` activity (at the end of the workflow, before `return`):

```python
        # Step 7: Create social event for reminders (non-blocking)
        try:
            await workflow.execute_activity(
                run_social_event, ctx,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=_DEFAULT_RETRY,
            )
        except Exception as exc:
            workflow.logger.warning("social_event_failed listing=%s error=%s", input.listing_id, exc)
```

- [ ] **Step 4: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/activities/social_event.py src/listingjet/activities/pipeline.py src/listingjet/workflows/listing_pipeline.py && git commit -m "feat: pipeline activity creates just_listed event with social reminders"
```

---

## Task 8: Listing Events API Router

**Files:**
- Create: `src/listingjet/api/listing_events.py`
- Create: `tests/test_api/test_listing_events.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_api/test_listing_events.py
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


def test_mark_posted_request_valid_platforms():
    from listingjet.api.schemas.social import MarkPostedRequest
    for p in ["instagram", "facebook", "tiktok"]:
        req = MarkPostedRequest(platform=p)
        assert req.platform == p


def test_mark_posted_request_rejects_invalid():
    from pydantic import ValidationError
    from listingjet.api.schemas.social import MarkPostedRequest
    with pytest.raises(ValidationError):
        MarkPostedRequest(platform="linkedin")


def test_create_event_request_valid_types():
    from listingjet.api.schemas.social import CreateListingEventRequest
    for t in ["open_house", "sold_pending"]:
        req = CreateListingEventRequest(event_type=t)
        assert req.event_type == t


def test_create_event_request_rejects_just_listed():
    from pydantic import ValidationError
    from listingjet.api.schemas.social import CreateListingEventRequest
    with pytest.raises(ValidationError):
        CreateListingEventRequest(event_type="just_listed")
```

- [ ] **Step 2: Create the router**

```python
# src/listingjet/api/listing_events.py
"""Listing events router — create events, list events, mark platforms as posted."""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.social import (
    CreateListingEventRequest,
    ListingEventResponse,
    MarkPostedRequest,
)
from listingjet.database import get_db
from listingjet.models.listing import Listing
from listingjet.models.listing_event import ListingEvent
from listingjet.models.user import User
from listingjet.services.social_reminder import SocialReminderService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{listing_id}/events", status_code=201, response_model=ListingEventResponse)
async def create_listing_event(
    listing_id: uuid.UUID,
    body: CreateListingEventRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a listing event (open_house, sold_pending). Triggers social reminders."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    event = ListingEvent(
        tenant_id=current_user.tenant_id,
        listing_id=listing_id,
        event_type=body.event_type,
        event_data=body.event_data,
    )
    db.add(event)
    await db.flush()

    # Create notification
    address = listing.address.get("street", "your listing")
    svc = SocialReminderService()
    svc.create_notification(
        session=db,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        listing_id=listing_id,
        event_type=body.event_type,
        address=address,
    )
    event.notified_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(event)

    # Send email (fire-and-forget)
    try:
        await svc.send_email_reminder(
            to_email=current_user.email,
            listing_id=listing_id,
            event_id=event.id,
            event_type=body.event_type,
            address=address,
        )
    except Exception:
        logger.exception("social reminder email failed for event %s", event.id)

    return ListingEventResponse.model_validate(event)


@router.get("/{listing_id}/events", response_model=list[ListingEventResponse])
async def list_listing_events(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all events for a listing."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    result = await db.execute(
        select(ListingEvent)
        .where(ListingEvent.listing_id == listing_id)
        .order_by(ListingEvent.created_at.desc())
    )
    events = result.scalars().all()
    return [ListingEventResponse.model_validate(e) for e in events]


@router.patch("/{listing_id}/events/{event_id}/posted", response_model=ListingEventResponse)
async def mark_posted(
    listing_id: uuid.UUID,
    event_id: uuid.UUID,
    body: MarkPostedRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a platform as posted for a listing event. Idempotent."""
    event = (await db.execute(
        select(ListingEvent).where(
            ListingEvent.id == event_id,
            ListingEvent.listing_id == listing_id,
            ListingEvent.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    platforms = list(event.posted_platforms)
    if body.platform not in platforms:
        platforms.append(body.platform)
        event.posted_platforms = platforms

    await db.commit()
    await db.refresh(event)
    return ListingEventResponse.model_validate(event)
```

- [ ] **Step 3: Run tests**

Run: `cd C:/Users/Jeff/launchlens && python -m pytest tests/test_api/test_listing_events.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/api/listing_events.py tests/test_api/test_listing_events.py && git commit -m "feat: listing events API — create, list, mark as posted"
```

---

## Task 9: Notifications API Router

**Files:**
- Create: `src/listingjet/api/notifications.py`

- [ ] **Step 1: Create the router**

```python
# src/listingjet/api/notifications.py
"""Notifications router — list, mark read."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.social import NotificationListResponse, NotificationResponse
from listingjet.database import get_db
from listingjet.models.notification import Notification
from listingjet.models.user import User

router = APIRouter()


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    unread: bool = False,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List notifications for the current user."""
    query = select(Notification).where(
        Notification.user_id == current_user.id,
        Notification.tenant_id == current_user.tenant_id,
    )
    if unread:
        query = query.where(Notification.read_at.is_(None))

    query = query.order_by(Notification.created_at.desc()).limit(min(limit, 50))
    result = await db.execute(query)
    items = result.scalars().all()

    # Unread count
    count_result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id,
            Notification.tenant_id == current_user.tenant_id,
            Notification.read_at.is_(None),
        )
    )
    unread_count = count_result.scalar() or 0

    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
        unread_count=unread_count,
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a single notification as read."""
    notif = (await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    if notif.read_at is None:
        notif.read_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(notif)
    return NotificationResponse.model_validate(notif)


@router.patch("/read-all")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read for the current user."""
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.tenant_id == current_user.tenant_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"status": "ok"}
```

- [ ] **Step 2: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/api/notifications.py && git commit -m "feat: notifications API — list, mark read, mark all read"
```

---

## Task 10: Social Accounts API Router

**Files:**
- Create: `src/listingjet/api/social_accounts.py`

- [ ] **Step 1: Create the router**

```python
# src/listingjet/api/social_accounts.py
"""Social accounts CRUD router — stubbed for future OAuth."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.social import CreateSocialAccountRequest, SocialAccountResponse
from listingjet.database import get_db
from listingjet.models.social_account import SocialAccount
from listingjet.models.user import User

router = APIRouter()


@router.get("", response_model=list[SocialAccountResponse])
async def list_social_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List connected social accounts for the current user."""
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.user_id == current_user.id,
            SocialAccount.tenant_id == current_user.tenant_id,
        ).order_by(SocialAccount.created_at)
    )
    accounts = result.scalars().all()
    return [SocialAccountResponse.model_validate(a) for a in accounts]


@router.post("", status_code=201, response_model=SocialAccountResponse)
async def create_or_update_social_account(
    body: CreateSocialAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update a social account (upsert by user + platform)."""
    existing = (await db.execute(
        select(SocialAccount).where(
            SocialAccount.user_id == current_user.id,
            SocialAccount.platform == body.platform,
        )
    )).scalar_one_or_none()

    if existing:
        existing.platform_username = body.platform_username
        existing.status = "pending"
        await db.commit()
        await db.refresh(existing)
        return SocialAccountResponse.model_validate(existing)

    account = SocialAccount(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        platform=body.platform,
        platform_username=body.platform_username,
        status="pending",
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return SocialAccountResponse.model_validate(account)


@router.delete("/{account_id}", status_code=200)
async def delete_social_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a connected social account."""
    account = (await db.execute(
        select(SocialAccount).where(
            SocialAccount.id == account_id,
            SocialAccount.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Social account not found")

    await db.delete(account)
    await db.commit()
    return {"deleted": True}
```

- [ ] **Step 2: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/api/social_accounts.py && git commit -m "feat: social accounts CRUD API (stubbed for future OAuth)"
```

---

## Task 11: Auto-Detect Price Change on Listing Update

**Files:**
- Modify: `src/listingjet/api/listings_core.py` (update_listing endpoint)

- [ ] **Step 1: Add price change detection**

In `src/listingjet/api/listings_core.py`, in the `update_listing` endpoint, after the metadata update and before `await db.commit()`, add price change detection:

```python
    # Auto-detect price change for social reminders
    if body.metadata is not None:
        new_meta = body.metadata.model_dump(exclude_none=True)
        old_price = (listing.metadata_ or {}).get("price")
        new_price = new_meta.get("price")
        if new_price is not None and old_price is not None and new_price != old_price:
            from listingjet.models.listing_event import ListingEvent
            price_event = ListingEvent(
                tenant_id=current_user.tenant_id,
                listing_id=listing_id,
                event_type="price_change",
                event_data={"old_price": old_price, "new_price": new_price},
            )
            db.add(price_event)
```

- [ ] **Step 2: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/api/listings_core.py && git commit -m "feat: auto-detect price changes and create listing events"
```

---

## Task 12: Register All New Routers

**Files:**
- Modify: `src/listingjet/main.py`

- [ ] **Step 1: Register the three new routers**

Add imports and include_router calls following the existing pattern:

```python
from listingjet.api.listing_events import router as listing_events_router
from listingjet.api.notifications import router as notifications_router
from listingjet.api.social_accounts import router as social_accounts_router
```

```python
app.include_router(listing_events_router, prefix="/listings", tags=["listing-events"])
app.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
app.include_router(social_accounts_router, prefix="/social-accounts", tags=["social-accounts"])
```

- [ ] **Step 2: Verify all imports**

Run: `cd C:/Users/Jeff/launchlens && python -c "from listingjet.main import app; print('App OK')"`
Expected: `App OK`

- [ ] **Step 3: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/main.py && git commit -m "feat: register listing events, notifications, social accounts routers"
```

---

## Task 13: Frontend — API Client Methods

**Files:**
- Modify: `frontend/src/lib/api-client.ts`

- [ ] **Step 1: Read the existing API client to understand patterns**

Read `frontend/src/lib/api-client.ts` and note the method pattern.

- [ ] **Step 2: Add new methods**

Add these methods following the existing pattern (use `as any` for untyped paths):

```typescript
  // Listing Events
  async createListingEvent(listingId: string, eventType: string, eventData: Record<string, any> = {}) {
    const { data, error } = await this.client.POST("/listings/{listing_id}/events" as any, {
      params: { path: { listing_id: listingId } },
      body: { event_type: eventType, event_data: eventData },
    });
    if (error) throw this.toError(error);
    return data as any;
  }

  async getListingEvents(listingId: string) {
    const { data, error } = await this.client.GET("/listings/{listing_id}/events" as any, {
      params: { path: { listing_id: listingId } },
    });
    if (error) throw this.toError(error);
    return data as any[];
  }

  async markEventPosted(listingId: string, eventId: string, platform: string) {
    const { data, error } = await this.client.PATCH("/listings/{listing_id}/events/{event_id}/posted" as any, {
      params: { path: { listing_id: listingId, event_id: eventId } },
      body: { platform },
    });
    if (error) throw this.toError(error);
    return data as any;
  }

  // Notifications
  async getNotifications(unread: boolean = false) {
    const { data, error } = await this.client.GET("/notifications" as any, {
      params: { query: { unread } },
    });
    if (error) throw this.toError(error);
    return data as any;
  }

  async markNotificationRead(notificationId: string) {
    const { data, error } = await this.client.PATCH("/notifications/{notification_id}/read" as any, {
      params: { path: { notification_id: notificationId } },
    });
    if (error) throw this.toError(error);
    return data as any;
  }

  async markAllNotificationsRead() {
    const { data, error } = await this.client.PATCH("/notifications/read-all" as any, {});
    if (error) throw this.toError(error);
    return data as any;
  }

  // Social Accounts
  async getSocialAccounts() {
    const { data, error } = await this.client.GET("/social-accounts" as any, {});
    if (error) throw this.toError(error);
    return data as any[];
  }

  async saveSocialAccount(platform: string, platformUsername: string) {
    const { data, error } = await this.client.POST("/social-accounts" as any, {
      body: { platform, platform_username: platformUsername },
    });
    if (error) throw this.toError(error);
    return data as any;
  }

  async deleteSocialAccount(accountId: string) {
    const { data, error } = await this.client.DELETE("/social-accounts/{account_id}" as any, {
      params: { path: { account_id: accountId } },
    });
    if (error) throw this.toError(error);
    return data as any;
  }
```

IMPORTANT: Match the exact error handling pattern in the existing file. The method may be `this.toError`, `this._toError`, or something else — read the file first.

- [ ] **Step 3: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add frontend/src/lib/api-client.ts && git commit -m "feat: add listing events, notifications, social accounts API client methods"
```

---

## Task 14: Frontend — Notification Bell Component

**Files:**
- Create: `frontend/src/hooks/use-notifications.ts`
- Create: `frontend/src/components/notifications/notification-bell.tsx`
- Modify: `frontend/src/components/layout/nav.tsx`

- [ ] **Step 1: Create notification polling hook**

```typescript
// frontend/src/hooks/use-notifications.ts
"use client";

import { useState, useEffect, useCallback } from "react";
import apiClient from "@/lib/api-client";

interface Notification {
  id: string;
  type: string;
  title: string;
  body: string;
  action_url: string | null;
  read_at: string | null;
  created_at: string;
}

export function useNotifications(pollInterval = 60000) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchNotifications = useCallback(async () => {
    try {
      const data = await apiClient.getNotifications(false);
      setNotifications(data.items || []);
      setUnreadCount(data.unread_count || 0);
    } catch {
      // Silently fail on poll errors
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, pollInterval);
    return () => clearInterval(interval);
  }, [fetchNotifications, pollInterval]);

  const markRead = useCallback(async (id: string) => {
    try {
      await apiClient.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n)),
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch {
      // ignore
    }
  }, []);

  const markAllRead = useCallback(async () => {
    try {
      await apiClient.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, read_at: n.read_at || new Date().toISOString() })));
      setUnreadCount(0);
    } catch {
      // ignore
    }
  }, []);

  return { notifications, unreadCount, markRead, markAllRead, refresh: fetchNotifications };
}
```

- [ ] **Step 2: Create notification bell component**

```typescript
// frontend/src/components/notifications/notification-bell.tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { useNotifications } from "@/hooks/use-notifications";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { notifications, unreadCount, markRead, markAllRead } = useNotifications();

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleNotificationClick = async (notif: (typeof notifications)[0]) => {
    if (!notif.read_at) {
      await markRead(notif.id);
    }
    setOpen(false);
    if (notif.action_url) {
      router.push(notif.action_url);
    }
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors"
        aria-label="Notifications"
      >
        {/* Bell SVG */}
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="absolute right-0 top-full mt-2 w-80 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl shadow-lg overflow-hidden z-50"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
              <span className="text-sm font-medium text-[var(--color-text)]">Notifications</span>
              {unreadCount > 0 && (
                <button
                  onClick={markAllRead}
                  className="text-xs text-[var(--color-primary)] hover:underline"
                >
                  Mark all read
                </button>
              )}
            </div>
            <div className="max-h-80 overflow-y-auto">
              {notifications.length === 0 ? (
                <p className="px-4 py-6 text-sm text-[var(--color-text-secondary)] text-center">
                  No notifications yet
                </p>
              ) : (
                notifications.slice(0, 10).map((notif) => (
                  <button
                    key={notif.id}
                    onClick={() => handleNotificationClick(notif)}
                    className={`w-full text-left px-4 py-3 hover:bg-[var(--color-surface-hover)] transition-colors border-b border-[var(--color-border)] last:border-0 ${
                      !notif.read_at ? "bg-[var(--color-primary)]/5" : ""
                    }`}
                  >
                    <p className="text-sm font-medium text-[var(--color-text)] truncate">{notif.title}</p>
                    <p className="text-xs text-[var(--color-text-secondary)] mt-0.5 line-clamp-2">{notif.body}</p>
                  </button>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
```

- [ ] **Step 3: Add bell to nav**

Read `frontend/src/components/layout/nav.tsx` and add the `NotificationBell` component near the theme toggle / sign out area:

```typescript
import { NotificationBell } from "@/components/notifications/notification-bell";
```

Add `<NotificationBell />` in the nav bar, before the theme toggle.

- [ ] **Step 4: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add frontend/src/hooks/use-notifications.ts frontend/src/components/notifications/notification-bell.tsx frontend/src/components/layout/nav.tsx && git commit -m "feat: notification bell with polling and dropdown"
```

---

## Task 15: Frontend — Social Post Hub Page

**Files:**
- Create: `frontend/src/app/listings/[id]/social/page.tsx`
- Create: `frontend/src/components/listings/social-post-hub.tsx`
- Create: `frontend/src/components/listings/caption-hook-selector.tsx`
- Create: `frontend/src/components/listings/platform-post-card.tsx`

- [ ] **Step 1: Create caption hook selector**

```typescript
// frontend/src/components/listings/caption-hook-selector.tsx
"use client";

import { useState } from "react";

const HOOKS = ["storyteller", "data-driven", "luxury_minimalist", "urgency", "lifestyle"];
const HOOK_LABELS: Record<string, string> = {
  storyteller: "Storyteller",
  "data-driven": "Data-Driven",
  luxury_minimalist: "Luxury",
  urgency: "Urgency",
  lifestyle: "Lifestyle",
};

interface Props {
  captions: Record<string, string>;
  platform: string;
}

export function CaptionHookSelector({ captions, platform }: Props) {
  const storageKey = `caption-hook-${platform}`;
  const [selected, setSelected] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem(storageKey) || HOOKS[0];
    }
    return HOOKS[0];
  });

  const handleSelect = (hook: string) => {
    setSelected(hook);
    localStorage.setItem(storageKey, hook);
  };

  const caption = captions[selected] || captions[HOOKS[0]] || "";

  return (
    <div className="space-y-2">
      <div className="flex gap-1 flex-wrap">
        {HOOKS.map((hook) => (
          <button
            key={hook}
            onClick={() => handleSelect(hook)}
            className={`px-2 py-1 text-xs rounded-md transition-colors ${
              selected === hook
                ? "bg-[var(--color-primary)] text-white"
                : "bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]"
            }`}
          >
            {HOOK_LABELS[hook] || hook}
          </button>
        ))}
      </div>
      <p className="text-sm text-[var(--color-text)] whitespace-pre-wrap">{caption}</p>
    </div>
  );
}
```

- [ ] **Step 2: Create platform post card**

```typescript
// frontend/src/components/listings/platform-post-card.tsx
"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import { CaptionHookSelector } from "./caption-hook-selector";

interface SocialCut {
  platform: string;
  s3_key: string;
  width: number;
  height: number;
  url: string;
}

interface Props {
  platform: string;
  platformLabel: string;
  videoUrl: string | null;
  captions: Record<string, string>;
  hashtags: string[];
  posted: boolean;
  connectedUsername: string | null;
  onMarkPosted: () => void;
  onCopyCaption: (text: string) => void;
}

const PLATFORM_ICONS: Record<string, string> = {
  instagram: "IG",
  facebook: "FB",
  tiktok: "TT",
};

export function PlatformPostCard({
  platform,
  platformLabel,
  videoUrl,
  captions,
  hashtags,
  posted,
  connectedUsername,
  onMarkPosted,
  onCopyCaption,
}: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    const hookKeys = Object.keys(captions);
    const storageKey = `caption-hook-${platform}`;
    const selectedHook = (typeof window !== "undefined" && localStorage.getItem(storageKey)) || hookKeys[0];
    const caption = captions[selectedHook] || captions[hookKeys[0]] || "";
    const hashtagStr = hashtags.length > 0 ? "\n\n" + hashtags.join(" ") : "";
    const fullText = caption + hashtagStr;

    navigator.clipboard.writeText(fullText);
    setCopied(true);
    onCopyCaption(fullText);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <GlassCard tilt={false} className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-8 h-8 rounded-lg bg-[var(--color-primary)]/10 text-[var(--color-primary)] flex items-center justify-center text-xs font-bold">
            {PLATFORM_ICONS[platform] || platform[0].toUpperCase()}
          </span>
          <span className="font-medium text-[var(--color-text)]">{platformLabel}</span>
        </div>
        {connectedUsername && (
          <span className="text-xs text-[var(--color-text-secondary)]">@{connectedUsername}</span>
        )}
      </div>

      {/* Video preview */}
      {videoUrl ? (
        <div className="aspect-video rounded-lg overflow-hidden bg-black">
          <video src={videoUrl} controls className="w-full h-full object-contain" />
        </div>
      ) : (
        <div className="aspect-video rounded-lg bg-[var(--color-surface)] flex items-center justify-center text-[var(--color-text-secondary)] text-sm">
          Video not available
        </div>
      )}

      {/* Caption */}
      <CaptionHookSelector captions={captions} platform={platform} />

      {/* Hashtags */}
      {hashtags.length > 0 && (
        <p className="text-xs text-[var(--color-primary)]">{hashtags.join(" ")}</p>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <Button variant="secondary" onClick={handleCopy} className="flex-1 text-sm">
          {copied ? "Copied!" : "Copy Caption"}
        </Button>
        {videoUrl && (
          <a href={videoUrl} download className="flex-1">
            <Button variant="secondary" className="w-full text-sm">
              Download Video
            </Button>
          </a>
        )}
      </div>

      {/* Posted checkbox */}
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={posted}
          onChange={onMarkPosted}
          disabled={posted}
          className="rounded border-[var(--color-border)]"
        />
        <span className={`text-sm ${posted ? "text-green-600" : "text-[var(--color-text-secondary)]"}`}>
          {posted ? "Posted" : "Mark as posted"}
        </span>
      </label>
    </GlassCard>
  );
}
```

- [ ] **Step 3: Create social post hub**

```typescript
// frontend/src/components/listings/social-post-hub.tsx
"use client";

import { useState, useEffect, useCallback } from "react";
import apiClient from "@/lib/api-client";
import { useToast } from "@/components/ui/toast";
import { PlatformPostCard } from "./platform-post-card";

interface Props {
  listingId: string;
}

const PLATFORMS = [
  { key: "instagram", label: "Instagram", cutKey: "instagram_reels" },
  { key: "facebook", label: "Facebook", cutKey: "facebook" },
  { key: "tiktok", label: "TikTok", cutKey: "tiktok" },
];

export function SocialPostHub({ listingId }: Props) {
  const [events, setEvents] = useState<any[]>([]);
  const [socialContent, setSocialContent] = useState<any[]>([]);
  const [socialCuts, setSocialCuts] = useState<any[]>([]);
  const [socialAccounts, setSocialAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const fetchData = useCallback(async () => {
    try {
      const [eventsData, cutsData, accountsData] = await Promise.all([
        apiClient.getListingEvents(listingId),
        apiClient.getVideoSocialCuts(listingId).catch(() => []),
        apiClient.getSocialAccounts().catch(() => []),
      ]);
      setEvents(eventsData || []);
      setSocialCuts(cutsData || []);
      setSocialAccounts(accountsData || []);

      // Fetch social content (captions)
      try {
        const content = await apiClient.getSocialContent(listingId);
        setSocialContent(content || []);
      } catch {
        setSocialContent([]);
      }
    } catch {
      toast("Failed to load social data", "error");
    } finally {
      setLoading(false);
    }
  }, [listingId, toast]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const latestEvent = events[0];

  const getCaption = (platform: string): Record<string, string> => {
    // Use instagram captions for tiktok
    const lookupPlatform = platform === "tiktok" ? "instagram" : platform;
    const content = socialContent.find((c: any) => c.platform === lookupPlatform);
    if (!content?.caption) return {};
    // Caption is stored as JSON with hooks
    const caption = content.caption;
    if (typeof caption === "object" && caption.hooks) {
      return caption.hooks;
    }
    return { default: typeof caption === "string" ? caption : JSON.stringify(caption) };
  };

  const getHashtags = (platform: string): string[] => {
    const lookupPlatform = platform === "tiktok" ? "instagram" : platform;
    const content = socialContent.find((c: any) => c.platform === lookupPlatform);
    return content?.hashtags || [];
  };

  const getVideoUrl = (cutKey: string): string | null => {
    const cut = socialCuts.find((c: any) => c.platform === cutKey);
    return cut?.url || null;
  };

  const getConnectedUsername = (platform: string): string | null => {
    const account = socialAccounts.find((a: any) => a.platform === platform);
    return account?.platform_username || null;
  };

  const handleMarkPosted = async (platform: string) => {
    if (!latestEvent) return;
    try {
      await apiClient.markEventPosted(listingId, latestEvent.id, platform);
      setEvents((prev) =>
        prev.map((e) =>
          e.id === latestEvent.id
            ? { ...e, posted_platforms: [...(e.posted_platforms || []), platform] }
            : e,
        ),
      );
      toast(`Marked as posted on ${platform}`, "success");
    } catch {
      toast("Failed to mark as posted", "error");
    }
  };

  if (loading) {
    return <div className="text-center py-12 text-[var(--color-text-secondary)]">Loading social data...</div>;
  }

  const eventLabels: Record<string, string> = {
    just_listed: "Just Listed",
    open_house: "Open House",
    price_change: "Price Change",
    sold_pending: "Sold/Pending",
  };

  return (
    <div className="space-y-6">
      {/* Event banner */}
      {latestEvent && (
        <div className="rounded-xl bg-[var(--color-primary)]/5 border border-[var(--color-primary)]/20 p-4">
          <p className="font-medium text-[var(--color-text)]">
            {eventLabels[latestEvent.event_type] || latestEvent.event_type}
          </p>
          <p className="text-sm text-[var(--color-text-secondary)]">
            {new Date(latestEvent.created_at).toLocaleDateString()}
          </p>
        </div>
      )}

      {/* Platform cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {PLATFORMS.map(({ key, label, cutKey }) => (
          <PlatformPostCard
            key={key}
            platform={key}
            platformLabel={label}
            videoUrl={getVideoUrl(cutKey)}
            captions={getCaption(key)}
            hashtags={key !== "facebook" ? getHashtags(key) : []}
            posted={(latestEvent?.posted_platforms || []).includes(key)}
            connectedUsername={getConnectedUsername(key)}
            onMarkPosted={() => handleMarkPosted(key)}
            onCopyCaption={() => toast("Caption copied to clipboard", "success")}
          />
        ))}
      </div>

      {/* No events state */}
      {events.length === 0 && (
        <div className="text-center py-12">
          <p className="text-[var(--color-text-secondary)]">
            No social events yet. Events are created automatically when your listing is delivered.
          </p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Create the route page**

```typescript
// frontend/src/app/listings/[id]/social/page.tsx
"use client";

import { use } from "react";
import { SocialPostHub } from "@/components/listings/social-post-hub";

export default function SocialPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);

  return (
    <main className="min-h-screen bg-[var(--color-background)]">
      <div className="max-w-5xl mx-auto px-4 py-6">
        <a
          href={`/listings/${id}`}
          className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors"
        >
          &larr; Back to Listing
        </a>
        <h1 className="text-2xl font-bold text-[var(--color-text)] mt-4 mb-6">Social Post Hub</h1>
        <SocialPostHub listingId={id} />
      </div>
    </main>
  );
}
```

- [ ] **Step 5: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add frontend/src/components/listings/caption-hook-selector.tsx frontend/src/components/listings/platform-post-card.tsx frontend/src/components/listings/social-post-hub.tsx frontend/src/app/listings/[id]/social/page.tsx && git commit -m "feat: Social Post Hub with platform cards, caption hooks, and video download"
```

---

## Task 16: Frontend — Add Social Tab to Listing Detail

**Files:**
- Modify: `frontend/src/app/listings/[id]/page.tsx`

- [ ] **Step 1: Add Social link to listing detail**

Read `frontend/src/app/listings/[id]/page.tsx` and add a "Social" link/button in the feature panels section (the three-column grid). Add after the existing feature panels:

```typescript
{/* Social Post Hub */}
<a
  href={`/listings/${listing.id}/social`}
  className="rounded-xl border border-[var(--color-border)] p-4 hover:border-[var(--color-primary)] transition-colors block"
>
  <h3 className="font-medium text-[var(--color-text)]">Social Media</h3>
  <p className="text-sm text-[var(--color-text-secondary)] mt-1">
    View and share ready-to-post content for Instagram, Facebook, and TikTok
  </p>
</a>
```

Only show this when the listing state is in delivered-like states (after pipeline completes).

- [ ] **Step 2: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add frontend/src/app/listings/[id]/page.tsx && git commit -m "feat: add Social Media link to listing detail page"
```

---

## Task 17: Frontend — Connected Accounts Settings

**Files:**
- Create: `frontend/src/components/settings/connected-accounts.tsx`
- Modify: `frontend/src/app/settings/page.tsx`

- [ ] **Step 1: Create connected accounts component**

```typescript
// frontend/src/components/settings/connected-accounts.tsx
"use client";

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import apiClient from "@/lib/api-client";
import { useToast } from "@/components/ui/toast";

const PLATFORMS = [
  { key: "instagram", label: "Instagram", icon: "IG" },
  { key: "facebook", label: "Facebook", icon: "FB" },
  { key: "tiktok", label: "TikTok", icon: "TT" },
];

interface Account {
  id: string;
  platform: string;
  platform_username: string;
  status: string;
}

export function ConnectedAccounts() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const { toast } = useToast();

  const fetchAccounts = useCallback(async () => {
    try {
      const data = await apiClient.getSocialAccounts();
      setAccounts(data || []);
      const initial: Record<string, string> = {};
      (data || []).forEach((a: Account) => {
        initial[a.platform] = a.platform_username;
      });
      setInputs(initial);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  const handleSave = async (platform: string) => {
    const username = inputs[platform]?.trim();
    if (!username) return;
    setSaving(platform);
    try {
      await apiClient.saveSocialAccount(platform, username);
      toast(`${platform} account saved`, "success");
      await fetchAccounts();
    } catch {
      toast("Failed to save account", "error");
    } finally {
      setSaving(null);
    }
  };

  const handleDelete = async (platform: string) => {
    const account = accounts.find((a) => a.platform === platform);
    if (!account) return;
    try {
      await apiClient.deleteSocialAccount(account.id);
      setInputs((prev) => ({ ...prev, [platform]: "" }));
      toast(`${platform} account removed`, "success");
      await fetchAccounts();
    } catch {
      toast("Failed to remove account", "error");
    }
  };

  return (
    <GlassCard tilt={false} className="p-6 space-y-4">
      <h2 className="text-lg font-semibold text-[var(--color-text)]">Connected Accounts</h2>
      <p className="text-sm text-[var(--color-text-secondary)]">
        Link your social media accounts. Auto-posting coming soon — for now, we'll personalize your social reminders.
      </p>

      <div className="space-y-3">
        {PLATFORMS.map(({ key, label, icon }) => {
          const account = accounts.find((a) => a.platform === key);
          return (
            <div key={key} className="flex items-center gap-3">
              <span className="w-8 h-8 rounded-lg bg-[var(--color-primary)]/10 text-[var(--color-primary)] flex items-center justify-center text-xs font-bold flex-shrink-0">
                {icon}
              </span>
              <span className="text-sm font-medium text-[var(--color-text)] w-20">{label}</span>
              <div className="flex-1 flex items-center gap-2">
                <span className="text-[var(--color-text-secondary)] text-sm">@</span>
                <input
                  type="text"
                  value={inputs[key] || ""}
                  onChange={(e) => setInputs((prev) => ({ ...prev, [key]: e.target.value }))}
                  placeholder="username"
                  className="flex-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-sm"
                />
              </div>
              <Button
                variant="secondary"
                onClick={() => handleSave(key)}
                loading={saving === key}
                disabled={!inputs[key]?.trim()}
                className="text-sm"
              >
                Save
              </Button>
              {account && (
                <button
                  onClick={() => handleDelete(key)}
                  className="text-xs text-red-500 hover:underline"
                >
                  Remove
                </button>
              )}
              {account && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700">
                  Pending
                </span>
              )}
            </div>
          );
        })}
      </div>
    </GlassCard>
  );
}
```

- [ ] **Step 2: Add to settings page**

Read `frontend/src/app/settings/page.tsx` and add the ConnectedAccounts component. Import it and place it after the existing brand kit sections:

```typescript
import { ConnectedAccounts } from "./_components/connected-accounts";
```

Note: The component may need to be moved to `frontend/src/app/settings/_components/connected-accounts.tsx` to match the existing pattern. Check where other settings components live and follow that pattern.

Add `<ConnectedAccounts />` in the settings page layout.

- [ ] **Step 3: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add frontend/src/components/settings/connected-accounts.tsx frontend/src/app/settings/page.tsx && git commit -m "feat: Connected Accounts settings with Instagram, Facebook, TikTok"
```

---

## Task 18: Integration Verification

- [ ] **Step 1: Backend import check**

Run: `cd C:/Users/Jeff/launchlens && python -c "from listingjet.main import app; print('App OK')"`
Expected: `App OK`

- [ ] **Step 2: Backend tests**

Run: `cd C:/Users/Jeff/launchlens && python -m pytest tests/test_services/test_post_time_config.py tests/test_services/test_social_reminder.py tests/test_api/test_listing_events.py -v`
Expected: All pass

- [ ] **Step 3: Frontend type check**

Run: `cd C:/Users/Jeff/launchlens/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Frontend build**

Run: `cd C:/Users/Jeff/launchlens/frontend && npm run build`
Expected: Build succeeds, includes `/listings/[id]/social` route

- [ ] **Step 5: Fix any issues and commit**

```bash
cd C:/Users/Jeff/launchlens && git add -A && git commit -m "fix: integration fixes for Phase 2 social features"
```
