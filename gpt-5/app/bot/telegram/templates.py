from typing import List
from ..llm.schemas import TaskExtract
from ..scheduler.engine import next_occurrences
from ..scheduler.format import format_dt
from datetime import datetime, date


def _recurrence_summary(t: TaskExtract) -> str:
    if t.kind == "one_time":
        return f"on {t.date} at {t.time}"
    if t.kind == "daily":
        return f"every day at {t.time}"
    if t.kind == "weekday":
        return f"every weekday at {t.time}"
    if t.kind == "weekly":
        days = ",".join(t.dow or [])
        return f"on {days} at {t.time}"
    if t.kind == "every_n_days":
        a = t.date or "today"
        return f"every {t.n_days} days at {t.time} (anchor {a})"
    return "unsupported"


def build_clarifications(batch: List[TaskExtract]) -> str:
    lines = []
    lines.append("I need a few clarifications before I can schedule:")
    idx = 1
    for t in batch:
        needs = list(t.needs or [])
        if t.tag == "unsure" and "tag" not in needs:
            needs.append("tag")
        if not needs:
            continue
        qs = []
        if "time" in needs:
            qs.append("What time of day (HH:MM UTC)?")
        if "tag" in needs:
            qs.append("Is this [work] or [personal]?")
        if "anchor" in needs:
            qs.append("If it repeats every N days, what start date? If none, say 'use today'.")
        if "unsupported" in needs:
            qs.append("The recurrence you described is unsupported. Please restate using only: one-time, daily, weekday, weekly, or every N days.")
        if qs:
            lines.append(f"{idx}) \"{t.name}\" — " + " ".join(qs))
            idx += 1
    if idx == 1:
        return "Everything looks clear."
    return "\n".join(lines)


def build_proposed_list(batch: List[TaskExtract]) -> str:
    lines = []
    lines.append("Proposed Task List")
    lines.append("")
    i = 1
    for t in batch:
        lines.append(f"{i}) [{t.tag}] \"{t.name}\" — {_recurrence_summary(t)}")
        i += 1
    return "\n".join(lines)


def build_final_schedule(batch: List[TaskExtract], now_utc: datetime, holidays: List[date], anchor_date: date) -> str:
    lines = []
    lines.append("SCHEDULE (UTC)")
    lines.append("")
    i = 1
    hset = set(holidays)
    for t in batch:
        lines.append(f"{i}) [{t.tag}] \"{t.name}\"")
        tt = t
        if tt.kind == "every_n_days" and not tt.date:
            tt = TaskExtract(**{**t.model_dump(), "date": anchor_date.isoformat()})
        occ = next_occurrences(tt, now_utc, hset)
        if occ:
            times = "; ".join([format_dt(x) for x in occ])
            lines.append(f"   Next: {times}")
        else:
            lines.append("   Next: (none)")
        lines.append("")
        i += 1
    return "\n".join(lines).rstrip()
