EXTRACTION_SYSTEM = (
    "You extract tasks and recurrence rules from natural language. "
    "Supported kinds: one_time, daily, weekday, weekly, every_n_days. "
    "For weekly, use dow as any of Mon,Tue,Wed,Thu,Fri,Sat,Sun. "
    "For every_n_days, n_days>=2 and optional anchor date; if missing, mark needs with 'anchor'. "
    "Always require time-of-day; if missing, add 'time' to needs. "
    "Tag is work or personal or unsure; do not invent. "
    "If unsupported recurrence like monthly or nth weekday, set needs to ['unsupported'] and set kind to the closest valid or keep as is. "
    "Return a strict JSON array of objects matching the schema. "
)

SELF_REPAIR_SYSTEM = (
    "Fix the JSON to satisfy the schema exactly without changing meaning. "
    "Output only the corrected JSON array."
)

CLASSIFY_SYSTEM = (
    "Classify each task as work or personal when confident; otherwise unsure. "
    "Return a strict JSON array of {id:int, tag:'work'|'personal'|'unsure'}."
)

