"""Tests for the drip email scheduler service."""
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_drip_scheduler_returns_sent_count(db_session):
    """run_drip_emails should return an integer count."""
    with patch("listingjet.services.drip_scheduler.get_email_service") as mock_get:
        mock_svc = MagicMock()
        mock_svc.send_notification = MagicMock()
        mock_get.return_value = mock_svc

        from listingjet.services.drip_scheduler import run_drip_emails
        count = await run_drip_emails(db_session)

        assert isinstance(count, int)
        assert count >= 0
