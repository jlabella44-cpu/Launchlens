"""Kling AI image-to-video provider.
Ported from Juke Marketing Engine (app/services/video_generator.py).
"""

import asyncio
import logging
import time

import httpx
import jwt as pyjwt

from listingjet.config import settings

logger = logging.getLogger(__name__)


class KlingProvider:
    def __init__(
        self,
        access_key: str | None = None,
        secret_key: str | None = None,
        base_url: str | None = None,
    ):
        self._access_key = access_key or settings.kling_access_key
        self._secret_key = secret_key or settings.kling_secret_key
        self._base_url = base_url or settings.kling_api_base_url

    def _generate_jwt(self) -> str:
        now = int(time.time())
        payload = {
            "iss": self._access_key,
            "exp": now + 1800,  # 30 minutes
            "nbf": now - 5,
        }
        return pyjwt.encode(payload, self._secret_key, algorithm="HS256")

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._generate_jwt()}",
        }

    async def generate_clip(
        self,
        image_url: str,
        prompt: str,
        negative_prompt: str = "",
        camera_control: dict | None = None,
        duration: int = 5,
        mode: str = "pro",
        model_name: str = "kling-v2-5-turbo",
    ) -> str:
        """Submit an image-to-video task to Kling. Returns task_id."""
        body: dict = {
            "model_name": model_name,
            "image": image_url,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "cfg_scale": 0.5,
            "mode": mode,
            "duration": str(duration),
        }
        # Camera control is only supported on kling-v1 / kling-v1-6
        if camera_control and not model_name.startswith("kling-v2"):
            body["camera_control"] = {
                "type": "simple",
                "config": {
                    "horizontal": camera_control.get("horizontal", 0),
                    "vertical": 0,
                    "zoom": camera_control.get("zoom", 3),
                    "tilt": 0,
                    "pan": 0,
                    "roll": 0,
                },
            }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self._base_url}/v1/videos/image2video",
                headers=self._headers(),
                json=body,
            )
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Kling API error: {data}")
            return data["data"]["task_id"]

    async def poll_task(
        self,
        task_id: str,
        timeout: int = 300,
        interval: int = 5,
    ) -> dict | None:
        """Poll a Kling task until completion.

        Returns dict with url, duration, credits on success; None on timeout/failure.
        """
        start = time.time()
        async with httpx.AsyncClient(timeout=30) as client:
            while time.time() - start < timeout:
                resp = await client.get(
                    f"{self._base_url}/v1/videos/image2video/{task_id}",
                    headers=self._headers(),
                )
                data = resp.json()
                task_data = data.get("data", {})
                status = task_data.get("task_status")

                if status == "succeed":
                    videos = task_data.get("task_result", {}).get("videos", [])
                    if not videos:
                        return None
                    video = videos[0]
                    credits = task_data.get("final_unit_deduction")
                    logger.info(
                        "kling_clip_complete task=%s duration=%ss credits=%s",
                        task_id, video.get("duration"), credits,
                    )
                    return {
                        "url": video["url"],
                        "duration": video.get("duration"),
                        "credits": credits,
                    }
                elif status == "failed":
                    msg = task_data.get("task_status_msg", "unknown")
                    logger.warning("kling_task_failed task=%s reason=%s", task_id, msg)
                    return None

                await asyncio.sleep(interval)
        return None  # Timeout
