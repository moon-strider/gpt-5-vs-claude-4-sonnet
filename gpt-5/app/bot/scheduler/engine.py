from datetime import datetime, timedelta, date
from typing import List, Set
from ..llm.schemas import TaskExtract
from . import rules


def _shift_if_needed(dt: datetime, holidays: Set[date]) -> datetime:
    d = dt
    while d.weekday() >= 5 or d.date() in holidays:
        d = d + timedelta(days=1)
    return d


def next_occurrences(task: TaskExtract, now_utc: datetime, holidays: Set[date]) -> List[datetime]:
    out: List[datetime] = []
    kind = task.kind
    t = task.time
    if t is None:
        return out
    start_date = now_utc.date()
    gen = None
    if kind == "one_time":
        if task.date is None:
            return out
        y, m, d = [int(x) for x in task.date.split("-")]
        gen = rules.one_time(date(y, m, d), t)
    elif kind == "daily":
        gen = rules.daily(t, start_date)
    elif kind == "weekday":
        gen = rules.weekday(t, start_date)
    elif kind == "weekly":
        gen = rules.weekly(set(task.dow or []), t, start_date)
    elif kind == "every_n_days":
        anchor = start_date
        if task.date:
            y, m, d = [int(x) for x in task.date.split("-")]
            anchor = date(y, m, d)
        interval = task.n_days or 2
        gen = rules.every_n_days(interval, anchor, t, start_date)
    else:
        return out
    for candidate in gen:
        if candidate <= now_utc:
            continue
        v = candidate
        if task.tag == "work":
            v = _shift_if_needed(v, holidays)
            if v <= now_utc:
                continue
        out.append(v)
        if len(out) >= 3:
            break
    return out

