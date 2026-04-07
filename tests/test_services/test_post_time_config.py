from datetime import datetime
from zoneinfo import ZoneInfo
from listingjet.services.post_time_config import BEST_POST_TIMES, get_listing_timezone, find_next_post_window

def test_best_post_times_has_all_platforms():
    assert "instagram" in BEST_POST_TIMES
    assert "facebook" in BEST_POST_TIMES
    assert "tiktok" in BEST_POST_TIMES

def test_get_listing_timezone_east_coast():
    assert get_listing_timezone("NY") == ZoneInfo("America/New_York")

def test_get_listing_timezone_west_coast():
    assert get_listing_timezone("CA") == ZoneInfo("America/Los_Angeles")

def test_get_listing_timezone_central():
    assert get_listing_timezone("TX") == ZoneInfo("America/Chicago")

def test_get_listing_timezone_mountain():
    assert get_listing_timezone("CO") == ZoneInfo("America/Denver")

def test_get_listing_timezone_unknown_defaults_to_eastern():
    assert get_listing_timezone("XX") == ZoneInfo("America/New_York")

def test_find_next_post_window_returns_datetime():
    now = datetime(2026, 4, 7, 3, 0, tzinfo=ZoneInfo("America/New_York"))  # Tuesday 3am
    result = find_next_post_window("instagram", now)
    assert result is not None
    assert result > now

def test_find_next_post_window_during_window_returns_now():
    now = datetime(2026, 4, 7, 11, 0, tzinfo=ZoneInfo("America/New_York"))  # Tuesday 11am
    result = find_next_post_window("instagram", now)
    assert result is None  # Inside window = post now
