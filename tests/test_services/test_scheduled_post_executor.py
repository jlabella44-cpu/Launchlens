"""Tests for scheduled post executor background task."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from listingjet.services.scheduled_post_executor import ScheduledPostExecutor


@pytest.mark.asyncio
async def test_process_post_success():
    """Successfully published post updates status and stores URL."""
    executor = ScheduledPostExecutor(session_factory=MagicMock())

    post = MagicMock()
    post.id = uuid.uuid4()
    post.tenant_id = uuid.uuid4()
    post.platform = "instagram"
    post.caption = "Test"
    post.hashtags = []
    post.media_s3_keys = ["test.jpg"]
    post.status = "scheduled"
    post.retry_count = 0

    account = MagicMock()
    account.access_token_encrypted = "token"
    account.page_id = "page_123"

    session = AsyncMock()
    acct_result = MagicMock()
    acct_result.scalar_one_or_none.return_value = account
    session.execute = AsyncMock(return_value=acct_result)
    session.flush = AsyncMock()

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.platform_post_id = "ig_123"
    mock_result.platform_post_url = "https://instagram.com/p/ig_123"

    with patch("listingjet.services.scheduled_post_executor.get_publisher") as mock_get:
        mock_publisher = AsyncMock()
        mock_publisher.publish = AsyncMock(return_value=mock_result)
        mock_get.return_value = mock_publisher

        await executor._process_post(session, post)

    assert post.status == "published"
    assert post.platform_post_id == "ig_123"
    assert post.published_at is not None


@pytest.mark.asyncio
async def test_process_post_failure_retries():
    """Failed post with retries left gets rescheduled."""
    executor = ScheduledPostExecutor(session_factory=MagicMock())

    post = MagicMock()
    post.id = uuid.uuid4()
    post.tenant_id = uuid.uuid4()
    post.platform = "facebook"
    post.status = "scheduled"
    post.retry_count = 0

    account = MagicMock()
    session = AsyncMock()
    acct_result = MagicMock()
    acct_result.scalar_one_or_none.return_value = account
    session.execute = AsyncMock(return_value=acct_result)
    session.flush = AsyncMock()

    mock_result = MagicMock()
    mock_result.success = False
    mock_result.error = "Rate limited"

    with patch("listingjet.services.scheduled_post_executor.get_publisher") as mock_get:
        mock_publisher = AsyncMock()
        mock_publisher.publish = AsyncMock(return_value=mock_result)
        mock_get.return_value = mock_publisher

        await executor._process_post(session, post)

    assert post.status == "scheduled"  # Rescheduled for retry
    assert post.retry_count == 1
    assert post.error_message == "Rate limited"


@pytest.mark.asyncio
async def test_process_post_no_account():
    """Post with no connected account fails immediately."""
    executor = ScheduledPostExecutor(session_factory=MagicMock())

    post = MagicMock()
    post.id = uuid.uuid4()
    post.tenant_id = uuid.uuid4()
    post.platform = "tiktok"
    post.status = "scheduled"

    session = AsyncMock()
    acct_result = MagicMock()
    acct_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=acct_result)
    session.flush = AsyncMock()

    await executor._process_post(session, post)

    assert post.status == "failed"
    assert "No connected" in post.error_message
