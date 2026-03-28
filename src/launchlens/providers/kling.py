"""Kling AI image-to-video provider.
Ported from Juke Marketing Engine (app/services/video_generator.py).
"""

import time
import asyncio
import jwt as pyjwt
import httpx
from launchlens.config import settings


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
    ) -> str:
        """Submit an image-to-video task to Kling. Returns task_id."""
        body: dict = {
            "model_name": "kling-v1",
            "image": image_url,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "cfg_scale": 0.5,
            "mode": mode,
            "duration": str(duration),
        }
        if camera_control:
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
    ) -> str | None:
        """Poll a Kling task until completion. Returns video URL or None on timeout."""
        start = time.time()
        async with httpx.AsyncClient(timeout=30) as client:
            while time.time() - start < timeout:
                resp = await client.get(
                    f"{self._base_url}/v1/videos/image2video/{task_id}",
                    headers=self._headers(),
                )
                data = resp.json()
                status = data.get("data", {}).get("task_status")

                if status == "succeed":
                    videos = data["data"].get("task_result", {}).get("videos", [])
                    return videos[0]["url"] if videos else None
                elif status == "failed":
                    return None

                await asyncio.sleep(interval)
        return None  # Timeout
