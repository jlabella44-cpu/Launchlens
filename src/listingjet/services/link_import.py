"""
Link-import service — download photos from third-party delivery links
(Google Drive, Show & Tour) and persist them to S3.
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from collections.abc import Callable

import httpx

from listingjet.services.storage import StorageService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

_GOOGLE_DRIVE_RE = re.compile(
    r"drive\.google\.com/drive/folders/(?P<id>[A-Za-z0-9_-]+)"
)
_SHOW_TOUR_RE = re.compile(
    r"(?:show\.tours|showandtour\.com)/(?P<id>[A-Za-z0-9_-]+)"
)


def detect_platform(url: str) -> str | None:
    """Return a platform key for *url*, or ``None`` if unrecognised."""
    if _GOOGLE_DRIVE_RE.search(url):
        return "google_drive"
    if _SHOW_TOUR_RE.search(url):
        return "show_tour"
    return None


# ---------------------------------------------------------------------------
# Google Drive importer
# ---------------------------------------------------------------------------

_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"


class GoogleDriveImporter:
    """Download images from a publicly-shared Google Drive folder."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def extract_folder_id(url: str) -> str:
        """Extract the folder ID from a Google Drive URL."""
        m = _GOOGLE_DRIVE_RE.search(url)
        if not m:
            raise ValueError(f"Cannot extract Google Drive folder ID from: {url}")
        return m.group("id")

    async def list_images(self, folder_id: str) -> list[dict]:
        """List image files inside *folder_id*."""
        import re
        if not re.fullmatch(r"[A-Za-z0-9_-]{10,80}", folder_id):
            raise ValueError(f"Invalid Google Drive folder ID: {folder_id}")
        params = {
            "q": f"'{folder_id}' in parents",
            "key": self.api_key,
            "fields": "files(id,name,mimeType)",
            "pageSize": 1000,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(_DRIVE_FILES_URL, params=params)
            resp.raise_for_status()
        files: list[dict] = resp.json().get("files", [])
        return [f for f in files if f.get("mimeType", "").startswith("image/")]

    async def download_file(self, file_id: str) -> tuple[str, bytes]:
        """Download a single file by *file_id*. Returns ``(filename, data)``."""
        url = f"{_DRIVE_FILES_URL}/{file_id}"
        params = {"alt": "media", "key": self.api_key}
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            # First, get metadata so we have the original filename.
            meta_resp = await client.get(
                url,
                params={"key": self.api_key, "fields": "name"},
            )
            meta_resp.raise_for_status()
            filename: str = meta_resp.json().get("name", f"{file_id}.jpg")

            # Then download the content.
            data_resp = await client.get(url, params=params)
            data_resp.raise_for_status()

        return filename, data_resp.content


# ---------------------------------------------------------------------------
# Show & Tour importer
# ---------------------------------------------------------------------------

_SHOW_TOUR_API = "https://show.tours/api/v2/download"


class ShowTourImporter:
    """Download images from a Show & Tour delivery link."""

    @staticmethod
    def extract_project_id(url: str) -> str:
        """Extract the project ID from a show.tours URL."""
        m = _SHOW_TOUR_RE.search(url)
        if not m:
            raise ValueError(f"Cannot extract Show & Tour project ID from: {url}")
        return m.group("id")

    async def list_images(self, url: str) -> list[dict]:
        """Fetch the image list for a delivery URL."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                _SHOW_TOUR_API,
                params={"deliveryURL": url},
            )
            resp.raise_for_status()
        data = resp.json()
        # The API may return a list directly or nest under a key.
        if isinstance(data, list):
            return data
        return data.get("images", data.get("files", []))

    async def download_file(self, image_url: str) -> tuple[str, bytes]:
        """Download an image from its direct URL."""
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
        # Derive filename from the URL path.
        filename = image_url.rstrip("/").rsplit("/", 1)[-1].split("?")[0] or "image.jpg"
        return filename, resp.content


# ---------------------------------------------------------------------------
# Main entry-point
# ---------------------------------------------------------------------------


async def import_from_link(
    url: str,
    platform: str,
    listing_id: str,
    storage: StorageService,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[dict]:
    """Download all photos from a delivery link and upload them to S3.

    Returns a list of ``{"file_path": <s3_key>, "file_hash": <sha256_hex>}``
    dicts for every successfully imported file.
    """

    batch_id = str(uuid.uuid4())
    results: list[dict] = []

    # -- resolve importer & file list ----------------------------------------
    if platform == "google_drive":
        importer = GoogleDriveImporter(api_key=_require_google_api_key())
        folder_id = importer.extract_folder_id(url)
        images = await importer.list_images(folder_id)
        total = len(images)

        for idx, img in enumerate(images, 1):
            try:
                filename, data = await importer.download_file(img["id"])
                s3_key = _upload(storage, listing_id, batch_id, filename, data)
                file_hash = hashlib.sha256(data).hexdigest()
                results.append({"file_path": s3_key, "file_hash": file_hash})
            except Exception:
                logger.exception(
                    "Failed to import Google Drive file %s — skipping",
                    img.get("id"),
                )
            if on_progress is not None:
                on_progress(idx, total)

    elif platform == "show_tour":
        importer_st = ShowTourImporter()
        images = await importer_st.list_images(url)
        total = len(images)

        for idx, img in enumerate(images, 1):
            image_url = img if isinstance(img, str) else img.get("url", img.get("src", ""))
            if not image_url:
                logger.warning("Show & Tour image entry has no URL — skipping: %s", img)
                if on_progress is not None:
                    on_progress(idx, total)
                continue
            try:
                filename, data = await importer_st.download_file(image_url)
                s3_key = _upload(storage, listing_id, batch_id, filename, data)
                file_hash = hashlib.sha256(data).hexdigest()
                results.append({"file_path": s3_key, "file_hash": file_hash})
            except Exception:
                logger.exception(
                    "Failed to import Show & Tour image %s — skipping",
                    image_url,
                )
            if on_progress is not None:
                on_progress(idx, total)

    else:
        raise ValueError(f"Unsupported platform: {platform!r}")

    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_google_api_key() -> str:
    """Return the configured Google API key or raise."""
    from listingjet.config import settings  # deferred to avoid circular imports

    key = settings.google_vision_api_key
    if not key:
        raise RuntimeError(
            "Google API key is not configured (settings.google_vision_api_key)"
        )
    return key


def _upload(
    storage: StorageService,
    listing_id: str,
    batch_id: str,
    filename: str,
    data: bytes,
) -> str:
    """Upload *data* to S3 and return the key."""
    content_type = _guess_content_type(filename)
    key = f"listings/{listing_id}/imports/{batch_id}/{filename}"
    return storage.upload(key, data, content_type)


def _guess_content_type(filename: str) -> str:
    """Return a MIME type based on the file extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "heic": "image/heic",
        "gif": "image/gif",
        "tiff": "image/tiff",
        "tif": "image/tiff",
        "bmp": "image/bmp",
    }.get(ext, "application/octet-stream")
