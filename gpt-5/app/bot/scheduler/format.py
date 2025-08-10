from datetime import datetime


def format_dt(dt: datetime) -> str:
    return f"{dt.strftime('%a')}, {dt.day} {dt.strftime('%b %Y, %H:%M')} (UTC+00:00, UTC)"

