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


# -- Show & Tour HTML scraping tests ----------------------------------------


@pytest.mark.asyncio
async def test_show_tour_list_images_from_html(httpx_mock):
    """ShowTourImporter extracts image URLs from an HTML delivery page."""
    html = """
    <html>
    <head>
        <meta property="og:image" content="https://cdn.showandtour.com/photos/hero.jpg" />
    </head>
    <body>
        <img src="https://cdn.showandtour.com/photos/living_room.jpg" />
        <img src="https://cdn.showandtour.com/photos/kitchen.png?w=1200" />
        <img src="https://cdn.showandtour.com/photos/bedroom.jpeg" />
        <img src="/static/favicon.png" />
        <img src="https://cdn.showandtour.com/icons/logo.png" />
    </body>
    </html>
    """
    httpx_mock.add_response(url="https://show.tours/LLuh6mqts0vonNo3urLm", text=html)

    importer = ShowTourImporter()
    urls = await importer.list_images("https://show.tours/LLuh6mqts0vonNo3urLm")

    # Should find 4 real photos, skip favicon and logo
    assert len(urls) == 4
    assert any("hero.jpg" in u for u in urls)
    assert any("living_room.jpg" in u for u in urls)
    assert any("kitchen.png" in u for u in urls)
    assert any("bedroom.jpeg" in u for u in urls)
    assert not any("favicon" in u for u in urls)
    assert not any("logo" in u for u in urls)


@pytest.mark.asyncio
async def test_show_tour_list_images_deduplicates(httpx_mock):
    """Duplicate image URLs (differing only by query params) are collapsed."""
    html = """
    <html><body>
        <img src="https://cdn.example.com/photo.jpg?w=800" />
        <img src="https://cdn.example.com/photo.jpg?w=1200" />
        <img src="https://cdn.example.com/other.jpg" />
    </body></html>
    """
    httpx_mock.add_response(url="https://show.tours/abc", text=html)

    importer = ShowTourImporter()
    urls = await importer.list_images("https://show.tours/abc")

    assert len(urls) == 2


@pytest.mark.asyncio
async def test_show_tour_list_images_empty_page(httpx_mock):
    """A page with no images returns an empty list."""
    httpx_mock.add_response(url="https://show.tours/empty", text="<html><body>No photos</body></html>")

    importer = ShowTourImporter()
    urls = await importer.list_images("https://show.tours/empty")

    assert urls == []


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
