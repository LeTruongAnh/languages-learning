"""'Today' must always be computed in the user's timezone, never the
server's (PLAN.md §1.2#5)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TZ = "Asia/Ho_Chi_Minh"


def today_in_tz(tz_name: str | None) -> date:
    try:
        tz = ZoneInfo(tz_name or DEFAULT_TZ)
    except (ZoneInfoNotFoundError, ValueError):
        tz = ZoneInfo(DEFAULT_TZ)
    return datetime.now(tz).date()
