"""Tests for the link_import service — platform detection and URL parsing."""
from listingjet.services.link_import import (
    GoogleDriveImporter,
    ShowTourImporter,
    detect_platform,
)


def test_detect_google_drive():
    assert detect_platform("https://drive.google.com/drive/folders/abc123") == "google_drive"


def test_detect_show_tour():
    assert detect_platform("https://show.tours/delivery/xyz") == "show_tour"


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
