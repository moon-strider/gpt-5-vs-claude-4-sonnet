from datetime import datetime


def format_dt(dt: datetime) -> str:
    return dt.strftime('%b %d, %Y at %H:%M GMT')
