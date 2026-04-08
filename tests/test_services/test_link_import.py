"""Tests for the link_import service — platform detection and URL parsing."""
import io
import zipfile

import pytest

from listingjet.services.link_import import (
    DropboxImporter,
    GoogleDriveImporter,
    ShowTourImporter,
    detect_platform,
)


def test_detect_google_drive():
    assert detect_platform("https://drive.google.com/drive/folders/abc123") == "google_drive"


def test_detect_show_tour():
    assert detect_platform("https://show.tours/delivery/xyz") == "show_tour"


def test_detect_dropbox_sh():
    assert detect_platform("https://www.dropbox.com/sh/abc123xyz/AABB?dl=0") == "dropbox"


def test_detect_dropbox_scl():
    assert detect_platform("https://www.dropbox.com/scl/fo/abc123xyz/AABB?dl=0") == "dropbox"


def test_detect_dropbox_no_www():
    assert detect_platform("https://dropbox.com/sh/abc123") == "dropbox"


def test_detect_unknown():
    assert detect_platform("https://random-site.com/photos") is None


def test_detect_empty():
    assert detect_platform("") is None


def test_google_drive_extract_folder_id():
    url = "https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQr"
    folder_id = GoogleDriveImporter.extract_folder_id(url)
    assert folder_id == "1AbCdEfGhIjKlMnOpQr"


def test_show_tour_extract_project_id():
    # Regex captures first path segment after domain as the ID
    url = "https://show.tours/proj-456"
    project_id = ShowTourImporter.extract_project_id(url)
    assert project_id == "proj-456"


# -- Dropbox importer unit tests -------------------------------------------


def test_dropbox_to_direct_url():
    url = "https://www.dropbox.com/sh/abc123/AABB?dl=0"
    direct = DropboxImporter._to_direct_url(url)
    assert direct == "https://www.dropbox.com/sh/abc123/AABB?dl=1"


def test_dropbox_to_direct_url_no_query():
    url = "https://www.dropbox.com/sh/abc123/AABB"
    direct = DropboxImporter._to_direct_url(url)
    assert direct == "https://www.dropbox.com/sh/abc123/AABB?dl=1"


def test_dropbox_is_image():
    assert DropboxImporter._is_image("photo.jpg") is True
    assert DropboxImporter._is_image("photo.JPEG") is True
    assert DropboxImporter._is_image("photo.png") is True
    assert DropboxImporter._is_image("photo.webp") is True
    assert DropboxImporter._is_image("photo.heic") is True
    assert DropboxImporter._is_image("readme.txt") is False
    assert DropboxImporter._is_image("data.csv") is False
    assert DropboxImporter._is_image("noext") is False


@pytest.mark.asyncio
async def test_dropbox_download_folder_zip(httpx_mock):
    """DropboxImporter extracts images from a ZIP response."""
    # Build a ZIP in memory with 2 images and 1 non-image
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("photos/living_room.jpg", b"\xff\xd8\xff\xe0JFIF-FAKE")
        zf.writestr("photos/kitchen.png", b"\x89PNG-FAKE")
        zf.writestr("photos/readme.txt", b"ignore me")
        zf.writestr("photos/.DS_Store", b"ignore me too")
    buf.seek(0)

    httpx_mock.add_response(
        url="https://www.dropbox.com/sh/test123/AABB?dl=1",
        content=buf.read(),
    )

    importer = DropboxImporter()
    images = await importer.download_folder_zip(
        "https://www.dropbox.com/sh/test123/AABB?dl=0"
    )

    assert len(images) == 2
    names = [name for name, _ in images]
    assert "living_room.jpg" in names
    assert "kitchen.png" in names
