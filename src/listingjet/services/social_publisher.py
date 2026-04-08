"""Social media publishers — publish posts to Instagram, Facebook, TikTok.

Each publisher handles media upload + post creation for its platform.
MockPublisher available for testing (USE_MOCK_PROVIDERS=true).
"""
from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from listingjet.config import settings
from listingjet.models.scheduled_post import ScheduledPost
from listingjet.models.social_account import SocialAccount
from listingjet.services.storage import StorageService

logger = logging.getLogger(__name__)


@dataclass
class PublishResult:
    success: bool
    platform_post_id: str | None = None
    platform_post_url: str | None = None
    error: str | None = None


class SocialPublisher(ABC):
    """Base class for platform-specific publishers."""

    @abstractmethod
    async def publish(self, account: SocialAccount, post: ScheduledPost) -> PublishResult:
        """Publish a post to the platform. Returns result with post URL or error."""

    async def _get_media_url(self, s3_key: str) -> str:
        """Generate a public presigned URL for media upload to platforms."""
        storage = StorageService()
        return storage.presigned_url(s3_key, expires=3600)


class InstagramPublisher(SocialPublisher):
    """Publish to Instagram via Meta Content Publishing API."""

    async def publish(self, account: SocialAccount, post: ScheduledPost) -> PublishResult:
        try:
            token = account.access_token_encrypted  # TODO: decrypt
            ig_user_id = account.page_id
            if not token or not ig_user_id:
                return PublishResult(success=False, error="Instagram account not fully connected")

            media_urls = []
            for key in post.media_s3_keys:
                media_urls.append(await self._get_media_url(key))

            if not media_urls:
                return PublishResult(success=False, error="No media to publish")

            caption = post.caption
            if post.hashtags:
                caption += "\n\n" + " ".join(f"#{h}" for h in post.hashtags)

            async with httpx.AsyncClient() as client:
                # Step 1: Create media container
                is_video = any(k.endswith((".mp4", ".mov")) for k in post.media_s3_keys)
                container_params = {
                    "access_token": token,
                    "caption": caption,
                }
                if is_video:
                    container_params["media_type"] = "VIDEO"
                    container_params["video_url"] = media_urls[0]
                else:
                    container_params["image_url"] = media_urls[0]

                resp = await client.post(
                    f"https://graph.facebook.com/v21.0/{ig_user_id}/media",
                    data=container_params,
                )
                resp.raise_for_status()
                container_id = resp.json()["id"]

                # Step 2: Publish the container
                pub_resp = await client.post(
                    f"https://graph.facebook.com/v21.0/{ig_user_id}/media_publish",
                    data={"creation_id": container_id, "access_token": token},
                )
                pub_resp.raise_for_status()
                media_id = pub_resp.json()["id"]

                return PublishResult(
                    success=True,
                    platform_post_id=media_id,
                    platform_post_url=f"https://www.instagram.com/p/{media_id}/",
                )

        except httpx.HTTPStatusError as e:
            error_body = e.response.json() if e.response else {}
            error_msg = error_body.get("error", {}).get("message", str(e))
            logger.error("instagram.publish_failed: %s", error_msg)
            return PublishResult(success=False, error=error_msg)
        except Exception as e:
            logger.exception("instagram.publish_error")
            return PublishResult(success=False, error=str(e))


class FacebookPublisher(SocialPublisher):
    """Publish to Facebook Page via Graph API."""

    async def publish(self, account: SocialAccount, post: ScheduledPost) -> PublishResult:
        try:
            token = account.access_token_encrypted  # TODO: decrypt
            page_id = account.page_id
            if not token or not page_id:
                return PublishResult(success=False, error="Facebook page not connected")

            caption = post.caption
            if post.hashtags:
                caption += "\n\n" + " ".join(f"#{h}" for h in post.hashtags)

            media_urls = [await self._get_media_url(k) for k in post.media_s3_keys]

            async with httpx.AsyncClient() as client:
                is_video = any(k.endswith((".mp4", ".mov")) for k in post.media_s3_keys)

                if is_video and media_urls:
                    resp = await client.post(
                        f"https://graph.facebook.com/v21.0/{page_id}/videos",
                        data={"access_token": token, "description": caption, "file_url": media_urls[0]},
                    )
                elif media_urls:
                    resp = await client.post(
                        f"https://graph.facebook.com/v21.0/{page_id}/photos",
                        data={"access_token": token, "message": caption, "url": media_urls[0]},
                    )
                else:
                    resp = await client.post(
                        f"https://graph.facebook.com/v21.0/{page_id}/feed",
                        data={"access_token": token, "message": caption},
                    )
                resp.raise_for_status()
                post_id = resp.json().get("id", resp.json().get("post_id"))

                return PublishResult(
                    success=True,
                    platform_post_id=post_id,
                    platform_post_url=f"https://www.facebook.com/{post_id}" if post_id else None,
                )

        except httpx.HTTPStatusError as e:
            error_body = e.response.json() if e.response else {}
            error_msg = error_body.get("error", {}).get("message", str(e))
            logger.error("facebook.publish_failed: %s", error_msg)
            return PublishResult(success=False, error=error_msg)
        except Exception as e:
            logger.exception("facebook.publish_error")
            return PublishResult(success=False, error=str(e))


class TikTokPublisher(SocialPublisher):
    """Publish to TikTok via Content Posting API."""

    async def publish(self, account: SocialAccount, post: ScheduledPost) -> PublishResult:
        try:
            token = account.access_token_encrypted  # TODO: decrypt
            if not token:
                return PublishResult(success=False, error="TikTok account not connected")

            video_keys = [k for k in post.media_s3_keys if k.endswith((".mp4", ".mov"))]
            if not video_keys:
                return PublishResult(success=False, error="TikTok requires video content")

            video_url = await self._get_media_url(video_keys[0])
            caption = post.caption
            if post.hashtags:
                caption += " " + " ".join(f"#{h}" for h in post.hashtags)

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://open.tiktokapis.com/v2/post/publish/video/init/",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={
                        "post_info": {"title": caption[:150], "privacy_level": "PUBLIC_TO_EVERYONE"},
                        "source_info": {"source": "PULL_FROM_URL", "video_url": video_url},
                    },
                )
                resp.raise_for_status()
                data = resp.json().get("data", {})
                publish_id = data.get("publish_id")

                return PublishResult(
                    success=True,
                    platform_post_id=publish_id,
                    platform_post_url=None,  # TikTok doesn't return URL immediately
                )

        except httpx.HTTPStatusError as e:
            logger.error("tiktok.publish_failed: %s", e)
            return PublishResult(success=False, error=str(e))
        except Exception as e:
            logger.exception("tiktok.publish_error")
            return PublishResult(success=False, error=str(e))


class MockPublisher(SocialPublisher):
    """Mock publisher for testing — always succeeds."""

    async def publish(self, account: SocialAccount, post: ScheduledPost) -> PublishResult:
        mock_id = str(uuid.uuid4())[:8]
        return PublishResult(
            success=True,
            platform_post_id=f"mock_{post.platform}_{mock_id}",
            platform_post_url=f"https://{post.platform}.com/p/mock_{mock_id}",
        )


def get_publisher(platform: str) -> SocialPublisher:
    """Factory: return the right publisher for the platform."""
    if settings.use_mock_providers:
        return MockPublisher()
    publishers = {
        "instagram": InstagramPublisher(),
        "facebook": FacebookPublisher(),
        "tiktok": TikTokPublisher(),
    }
    return publishers.get(platform, MockPublisher())
