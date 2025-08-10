from datetime import datetime, timedelta, date, timezone, time as dtime


def _combine(d: date, t: str) -> datetime:
    hh, mm = t.split(":")
    return datetime(d.year, d.month, d.day, int(hh), int(mm), tzinfo=timezone.utc)


def daily(t: str, start_date: date):
    d = start_date
    while True:
        yield _combine(d, t)
        d = d + timedelta(days=1)


def weekday(t: str, start_date: date):
    d = start_date
    while True:
        if d.weekday() < 5:
            yield _combine(d, t)
        d = d + timedelta(days=1)


_DOW_MAP = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}


def weekly(dow_set: set[str], t: str, start_date: date):
    wanted = {_DOW_MAP[d] for d in dow_set}
    d = start_date
    while True:
        if d.weekday() in wanted:
            yield _combine(d, t)
        d = d + timedelta(days=1)


def every_n_days(interval: int, anchor_date: date, t: str, start_date: date):
    if start_date <= anchor_date:
        base = anchor_date
    else:
        delta = (start_date - anchor_date).days
        steps = (delta + interval - 1) // interval
        base = anchor_date + timedelta(days=steps * interval)
    d = base
    while True:
        yield _combine(d, t)
        d = d + timedelta(days=interval)


def one_time(dt_date: date, t: str):
    yield _combine(dt_date, t)
