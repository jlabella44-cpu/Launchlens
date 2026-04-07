"""Static best-time-to-post configuration and timezone mapping for social reminders."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

BEST_POST_TIMES: dict[str, list[dict]] = {
    "instagram": [
        {"days": ["tue", "wed", "thu"], "start": time(10, 0), "end": time(13, 0)},
        {"days": ["sat"], "start": time(9, 0), "end": time(11, 0)},
    ],
    "facebook": [
        {"days": ["tue", "wed", "thu"], "start": time(9, 0), "end": time(12, 0)},
        {"days": ["sat"], "start": time(10, 0), "end": time(12, 0)},
    ],
    "tiktok": [
        {"days": ["tue", "thu"], "start": time(14, 0), "end": time(17, 0)},
        {"days": ["fri", "sat"], "start": time(19, 0), "end": time(21, 0)},
    ],
}

_DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

_STATE_TZ: dict[str, str] = {
    **{s: "America/New_York" for s in ["CT","DE","FL","GA","IN","KY","ME","MD","MA","MI","NH","NJ","NY","NC","OH","PA","RI","SC","TN","VT","VA","WV","DC"]},
    **{s: "America/Chicago" for s in ["AL","AR","IL","IA","KS","LA","MN","MS","MO","NE","ND","OK","SD","TX","WI"]},
    **{s: "America/Denver" for s in ["AZ","CO","ID","MT","NM","UT","WY"]},
    **{s: "America/Los_Angeles" for s in ["CA","NV","OR","WA"]},
    "AK": "America/Anchorage",
    "HI": "Pacific/Honolulu",
}

def get_listing_timezone(state_code: str) -> ZoneInfo:
    tz_name = _STATE_TZ.get(state_code.upper(), "America/New_York")
    return ZoneInfo(tz_name)

def find_next_post_window(platform: str, now: datetime) -> datetime | None:
    windows = BEST_POST_TIMES.get(platform, [])
    current_day = _DAY_NAMES[now.weekday()]
    current_time = now.time()

    for window in windows:
        if current_day in window["days"] and window["start"] <= current_time < window["end"]:
            return None

    for days_ahead in range(0, 8):
        check_date = now + timedelta(days=days_ahead)
        check_day = _DAY_NAMES[check_date.weekday()]
        for window in windows:
            if check_day in window["days"]:
                window_start = check_date.replace(hour=window["start"].hour, minute=window["start"].minute, second=0, microsecond=0)
                if window_start > now:
                    return window_start

    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
