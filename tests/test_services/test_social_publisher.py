"""Tests for social publisher service — mock publisher and factory."""
from unittest.mock import MagicMock

import pytest

from listingjet.services.social_publisher import (
    MockPublisher,
    get_publisher,
)


def _mock_account(platform="instagram"):
    acct = MagicMock()
    acct.access_token_encrypted = "test_token"
    acct.page_id = "page_123"
    acct.platform = platform
    return acct


def _mock_post(platform="instagram", caption="Test caption", hashtags=None, media=None):
    post = MagicMock()
    post.platform = platform
    post.caption = caption
    post.hashtags = hashtags or []
    post.media_s3_keys = media or ["listings/abc/hero.jpg"]
    return post


@pytest.mark.asyncio
async def test_mock_publisher_always_succeeds():
    publisher = MockPublisher()
    result = await publisher.publish(_mock_account(), _mock_post())
    assert result.success is True
    assert result.platform_post_id is not None
    assert "mock" in result.platform_post_id
    assert result.platform_post_url is not None


@pytest.mark.asyncio
async def test_mock_publisher_includes_platform_in_id():
    publisher = MockPublisher()
    result = await publisher.publish(_mock_account("tiktok"), _mock_post("tiktok"))
    assert "tiktok" in result.platform_post_id


def test_get_publisher_returns_mock_when_enabled():
    from unittest.mock import patch
    with patch("listingjet.services.social_publisher.settings") as mock_settings:
        mock_settings.use_mock_providers = True
        publisher = get_publisher("instagram")
        assert isinstance(publisher, MockPublisher)


def test_get_publisher_returns_platform_specific():
    from unittest.mock import patch
    with patch("listingjet.services.social_publisher.settings") as mock_settings:
        mock_settings.use_mock_providers = False
        from listingjet.services.social_publisher import InstagramPublisher
        publisher = get_publisher("instagram")
        assert isinstance(publisher, InstagramPublisher)
