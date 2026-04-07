# tests/test_services/test_social_reminder.py
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo
import pytest
from listingjet.services.social_reminder import SocialReminderService

@pytest.fixture
def svc():
    return SocialReminderService()

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    return session

@pytest.mark.asyncio
async def test_create_notification(svc, mock_session):
    notif = svc.create_notification(
        session=mock_session, user_id=uuid.uuid4(), tenant_id=uuid.uuid4(),
        listing_id=uuid.uuid4(), event_type="just_listed", address="123 Main St",
    )
    mock_session.add.assert_called_once()
    assert notif.type == "social_reminder"
    assert "123 Main St" in notif.title

def test_should_send_followup_after_24h(svc):
    event = MagicMock()
    event.posted_platforms = []
    event.notified_at = datetime(2026, 4, 6, 10, 0, tzinfo=ZoneInfo("America/New_York"))
    event.followup_sent_at = None
    now = datetime(2026, 4, 7, 11, 0, tzinfo=ZoneInfo("America/New_York"))
    assert svc.should_send_followup(event, now) is True

def test_should_not_followup_if_posted(svc):
    event = MagicMock()
    event.posted_platforms = ["instagram"]
    event.notified_at = datetime(2026, 4, 6, 10, 0, tzinfo=ZoneInfo("America/New_York"))
    event.followup_sent_at = None
    now = datetime(2026, 4, 7, 11, 0, tzinfo=ZoneInfo("America/New_York"))
    assert svc.should_send_followup(event, now) is False

def test_should_not_followup_twice(svc):
    event = MagicMock()
    event.posted_platforms = []
    event.notified_at = datetime(2026, 4, 6, 10, 0, tzinfo=ZoneInfo("America/New_York"))
    event.followup_sent_at = datetime(2026, 4, 7, 10, 0, tzinfo=ZoneInfo("America/New_York"))
    now = datetime(2026, 4, 8, 10, 0, tzinfo=ZoneInfo("America/New_York"))
    assert svc.should_send_followup(event, now) is False
