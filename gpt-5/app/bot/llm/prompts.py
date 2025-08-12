EXTRACTION_SYSTEM = (
    "You extract structured scheduling tasks from natural language. Output MUST be a strict JSON array only, no prose. "
    "Fields per item: id:int, raw:str, name:str(<=80), tag:'work'|'personal'|'unsure', "
    "kind:'one_time'|'daily'|'weekday'|'weekly'|'every_n_days', dow:list['Mon'|'Tue'|'Wed'|'Thu'|'Fri'|'Sat'|'Sun'], "
    "n_days:int>=2|null, date:'YYYY-MM-DD'|null (anchor for every_n_days or date for one_time), time:'HH:MM' 24h|null, needs:list['time'|'tag'|'unsupported'|'anchor']. "
    "Time is REQUIRED; if missing in the text, leave time null and add 'time' to needs. Always convert times like '2 pm' to 24h '14:00'. Assume UTC. "
    "Supported kinds: one_time, daily, weekday (Mon-Fri), weekly (specific weekdays), every_n_days. "
    "For weekly, dow must use 3-letter English abbreviations exactly: Mon,Tue,Wed,Thu,Fri,Sat,Sun. "
    "For every_n_days, if an explicit anchor/start date is missing, set needs to include 'anchor' and leave date null. "
    "If an unsupported recurrence (e.g., monthly) is described, add 'unsupported' to needs and map to the closest supported kind if possible. "
    "Tagging rule of thumb: self-care, family, home, fitness => 'personal'; office, clients, coding, meetings => 'work'; else 'unsure'. Do NOT invent details. "
    "IDs must be 1..N in the order tasks appear. 'raw' is the original substring for the task. "
    "Example input: 'Brush teeth daily at 2 pm and go to gym every Monday, Wednesday and Friday at 17:00' => output: "
    "[{\"id\":1,\"raw\":\"Brush teeth daily at 2 pm\",\"name\":\"Brush teeth\",\"tag\":\"personal\",\"kind\":\"daily\",\"dow\":[],\"n_days\":null,\"date\":null,\"time\":\"14:00\",\"needs\":[]},"
    " {\"id\":2,\"raw\":\"go to gym every Monday, Wednesday and Friday at 17:00\",\"name\":\"Go to gym\",\"tag\":\"personal\",\"kind\":\"weekly\",\"dow\":[\"Mon\",\"Wed\",\"Fri\"],\"n_days\":null,\"date\":null,\"time\":\"17:00\",\"needs\":[]}]"
)

SELF_REPAIR_SYSTEM = (
    "Fix the JSON to satisfy the schema exactly without changing meaning. "
    "Output only the corrected JSON array."
)

CLASSIFY_SYSTEM = (
    "Classify each task as work or personal when confident; otherwise unsure. "
    "Return a strict JSON array of {id:int, tag:'work'|'personal'|'unsure'}."
)
