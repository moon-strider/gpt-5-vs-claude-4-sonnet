# Technical Specification — Telegram Scheduling Bot

## 1) Purpose & Contract

Per **single “batch session”** initiated by a user’s **text message**, the bot:

* Extracts **1+ tasks** written in natural language (multiple tasks may be on a single line).
* **Auto-classifies** each task as `[work]` or `[personal]` (LLM: GPT-5 via LangChain).
* If anything is missing/ambiguous, sends **one grouped clarification message** (natural language). User replies in **natural language**. This can repeat.
* When everything is resolvable, the bot shows a **Proposed Task List** and renders **inline buttons**:

  * **✅ Approve**  | callback\_data: `APR`
  * **❌ Reject**   | callback\_data: `REJ`
* On **Approve**, the bot sends **one final message** with the **next 3 run datetimes** per task (human-readable).
* On **Reject**, the bot ends the session and purges context.

**Statelessness (strict):**

* A **batch session** spans from the initial user text to one of: **Approve (and final schedule sent)**, **Reject**, or **/clear**.
* During a session, the bot may use **all messages in that session** (initial text, any clarifications/answers, and the latest `holidays.json` file).
* **No persistence** beyond the session: after the session ends, the bot treats subsequent messages as unrelated.

**Single active session per chat:**
If a new, non-command message arrives while a session is open, the bot treats it as part of the **current** session. To start fresh, the user must send **/clear**.

## 2) Platform & Runtime

* **Python**: 3.11
* **Telegram**: aiogram (3.x)
* **LLM**: GPT-5 via LangChain (`langchain`, `langchain-openai`)
* **Container**: Docker (see §12)
* **Storage**: none (no DB). Logs only.

## 3) Commands

* **/help** — shows usage, supported recurrences, `holidays.json` attachment rules, UTC timezone note, and Approve/Reject via inline buttons.
* **/clear** — immediately **ends and purges** the current session (if any). Replies “Session cleared.”

## 4) Input (Batch) Rules

* Initial message: **plain text**; tasks in natural language; **no headers and no DSL**.
* The user may attach exactly one **Telegram document named `holidays.json`** any time during the session (see §7). The **latest** valid file in the session is used.

## 5) Output & Dialog Flow (Natural Language Only)

### 5.1 Clarifications (grouped)

* If data is missing/ambiguous, the bot sends **one grouped clarification message** listing every unclear task and the exact questions, in plain English.
* The user answers in **natural language**. The bot repeats with a new grouped clarification only if still needed.

### 5.2 Proposed Task List & Inline Buttons

* When resolvable, the bot posts the **Proposed Task List** (normalized names + recurrences, still **no dates**), with an **inline keyboard**:

  * Row: **✅ Approve** (`APR`) | **❌ Reject** (`REJ`)
* On button press, the bot **answers the callback** (to stop the spinner), **edits** the proposal message to reflect the choice (e.g., “Approved ✅” / “Rejected ❌”), and proceeds accordingly.
  `callback_data` must be **≤ 64 bytes** per Telegram’s Bot API. ([Telegram][1])

### 5.3 Final Schedule (on Approve)

* Sends exactly **one** final message with **up to 3** next occurrences per task (format in §10).
* **No chunking**: if the message would exceed Telegram’s **4096-char** limit, return `OUTPUT_TOO_LONG`. ([Telegram Limits][2])

## 6) Time, Weekends, Tags, Shifting

* **Timezone**: **UTC** (`UTC`, offset `+00:00`), fixed and not user-configurable.
* **Weekends**: Saturday and Sunday.
* **Tags**: `[work]`, `[personal]`.
* **Shifting rule** (applies to `[work]` only):
  If a computed run falls on **weekend** or a **holiday** (§7), shift **forward** day-by-day to the next **non-holiday weekday**, keeping the **same UTC time**.

## 7) Holidays via File Attachment

* Accept **one document** named **`holidays.json`** (exact name) per message; the **latest** valid one in the **current session** is used.
* **Validation**:

  * File name: `holidays.json`
  * MIME type: `application/json`
  * Size: **≤ 256 KB** (bot-enforced)
* **Schema** (strict):

  ```json
  {
    "version": 1,
    "dates": [
      {"date": "YYYY-MM-DD", "name": "optional string"}
    ]
  }
  ```

  * `version` must be `1`.
  * Each `date` is ISO `YYYY-MM-DD`.
* Errors: `ATTACHMENT_MISSING`, `ATTACHMENT_INVALID`, `ATTACHMENT_MULTIPLE`, `ATTACHMENT_JSON_INVALID`, `HOLIDAYS_JSON_INVALID`.

## 8) Supported Recurrence Semantics

* **one\_time** — explicit date + time (e.g., “on 2025-08-12 at 10:00”).
* **daily** — “every day at HH\:MM”.
* **weekday** — “every weekday at HH\:MM”.
* **weekly** — “on Mon/Tue/... at HH\:MM” (any subset).
* **every\_n\_days** — “every N days at HH\:MM”, **N ≥ 2**.
  **Anchor**: if no start date is provided, **default anchor is “today” (UTC date of the session’s first user message)**.

**Out of scope** (rejected): monthly patterns, nth weekday, ranges, exceptions, offsets → per-task status `UNSUPPORTED_RECURRENCE`.

**Missing time-of-day** always requires clarification.

## 9) LLM Contracts (internal)

### 9.1 Extraction JSON (array per turn)

```json
[
  {
    "id": 1,
    "raw": "gym on Mondays at 19:00",
    "name": "Gym",                       // ≤ 80 chars, trimmed
    "tag": "work|personal|unsure",
    "kind": "one_time|daily|weekday|weekly|every_n_days",
    "dow": ["Mon"],                      // weekly only
    "n_days": 2,                         // every_n_days only
    "date": "2025-08-12",                // one_time or anchor for every_n_days
    "time": "19:00",                     // 24h
    "needs": []                          // ["time","tag","unsupported","anchor"]
  }
]
```

* One self-repair pass if invalid; on failure → `PARSE_FAILED`.

### 9.2 Classification

* GPT-5 assigns `[work]` or `[personal]`. If uncertain, it **asks a natural-language question** (no DSL/tags in user input).

### 9.3 Session prompt context

* LLM receives **all** messages since session start (initial text, all bot clarifications, all user replies, and the latest parsed holidays).
* **Prompt budget**: `MAX_PROMPT_TOKENS=24000`. If exceeded: `CONTEXT_TOO_LARGE` (ask user to shorten/restart with **/clear**).

## 10) Scheduling Algorithm (deterministic, UTC)

**Inputs:** normalized tasks JSON, **UTC**, weekend set, holidays set, and **now = Telegram receive timestamp** (UTC) of the **current** message.

For each task:

1. **Candidate generation**

   * `one_time`: exactly `date + time` (UTC).
   * `daily`: `FREQ=DAILY; BYHOUR, BYMINUTE`.
   * `weekday`: `FREQ=WEEKLY; BYDAY=MO,TU,WE,TH,FR; BYHOUR, BYMINUTE`.
   * `weekly`: `FREQ=WEEKLY; BYDAY=<dow set>; BYHOUR, BYMINUTE`.
   * `every_n_days`: `FREQ=DAILY; INTERVAL=n_days; BYHOUR, BYMINUTE` anchored at the **anchor date** (explicit date or “today” if omitted).
2. **No past scheduling**: skip any candidate **≤ now**.
3. **\[work] forward shift**: if candidate is **Sat/Sun** or in holidays, advance by days until a **non-holiday weekday**, keep time.
4. Return the **next 3** valid datetimes (fewer for one-time if not enough remain).

**Output date format (exact):**

```
EEE, d MMM yyyy, HH:mm (UTC+00:00, UTC)
```

## 11) Final Output (exact shape)

On Approve:

```
SCHEDULE (UTC)

1) [work] "Pay invoices"
   Next: Mon, 11 Aug 2025, 09:00 (UTC+00:00, UTC); Tue, 12 Aug 2025, 09:00 (UTC+00:00, UTC); Wed, 13 Aug 2025, 09:00 (UTC+00:00, UTC)

2) [personal] "Gym"
   Next: Mon, 11 Aug 2025, 19:00 (UTC+00:00, UTC); Mon, 18 Aug 2025, 19:00 (UTC+00:00, UTC); Mon, 25 Aug 2025, 19:00 (UTC+00:00, UTC)
```

If the outgoing message would exceed **4096 characters**, respond with `OUTPUT_TOO_LONG`. (Telegram limit evidence: **4096 chars** per message; **message markup** (inline buttons) up to **10 KB**.) ([Telegram Limits][2])

## 12) Docker & Ops

**Dockerfile**

* Base: `python:3.11-slim`
* Install minimal OS deps (certs), then `pip install`:

  * `aiogram`, `langchain`, `langchain-openai`, `python-dateutil`
* Non-root user; `WORKDIR /app`; copy code; `CMD ["python","-m","app"]`.

**Env vars (required unless noted):**

* `TELEGRAM_BOT_TOKEN`
* `OPENAI_API_KEY`
* `APP_TZ=UTC` (must be `UTC`)
* `LOG_LEVEL=INFO`
* `MAX_PROMPT_TOKENS=24000`

**Runtime**

* Logs to stdout (no message bodies at INFO/WARN; redact at DEBUG).
* Graceful shutdown on SIGTERM.
* Healthcheck: lightweight readiness check.

## 13) Telegram Limits (enforced)

* **Incoming user text** and **outgoing bot text** must be **≤ 4096 characters**. Otherwise:

  * incoming → `INPUT_TOO_LONG`
  * outgoing → `OUTPUT_TOO_LONG`
    Limits reference (2025): **4096 chars per message**, **inline keyboard data up to 10 KB**, **callback\_data up to 64 bytes**. ([Telegram Limits][2], [Telegram][1])

## 14) Errors & Status Codes

**Per-task (during clarifications):**
`OK` · `NEED_TIME` · `NEED_TAG` · `UNSUPPORTED_RECURRENCE` · `NEED_ANCHOR` · `PARSE_FAILED` · `DROPPED_BY_USER`

**Batch-level:**
`NO_TASKS_FOUND` · `ATTACHMENT_MISSING` · `ATTACHMENT_INVALID` · `ATTACHMENT_MULTIPLE` · `ATTACHMENT_JSON_INVALID` · `HOLIDAYS_JSON_INVALID` · `INPUT_TOO_LONG` · `OUTPUT_TOO_LONG` · `CONTEXT_TOO_LARGE` · `SESSION_IN_PROGRESS`

## 15) Acceptance Tests (deterministic)

1. **Weekday shift (work)**
   Given `[work] every weekday at 09:00`, `now = Fri 2025-08-08 14:00 UTC` → next = **Mon, 11 Aug 2025, 09:00**, then Tue 09:00, Wed 09:00.
2. **Holiday shift (work)**
   With `holidays.json` containing `2025-08-11`, and weekly `[work]` on Mon 10:00 → next = **Tue, 12 Aug 2025, 10:00**.
3. **Past-today avoidance**
   “today at 09:00” with `now = 14:00` → next = **tomorrow 09:00**.
4. **every\_n\_days with default anchor**
   “every 3 days at 07:30” with **no start date**, `now = 2025-08-09 14:00 UTC` → anchor = **2025-08-09** (today); next 3: **Sun 10 Aug 07:30**, **Wed 13 Aug 07:30**, **Sat 16 Aug 07:30**.
5. **Unsupported recurrence**
   “last Friday of each month at 18:00” → `UNSUPPORTED_RECURRENCE`.
6. **Inline Approve/Reject**
   Proposed list message shows **✅ Approve** (`APR`) and **❌ Reject** (`REJ`). On Approve, bot edits the proposal message to reflect approval, disables buttons, and sends the final SCHEDULE. `callback_data` length stays **< 64 bytes**. ([Telegram][1])
7. **Length overrun**
   If the final schedule text would exceed **4096 chars**, bot returns `OUTPUT_TOO_LONG`. ([Telegram Limits][2])

---

## Notes locked by spec

* **UTC only**, **no headers**, **no DSL**, **inline buttons** for decisions, **/clear** for manual purge, **no chunking**, **no monthly/advanced rules**, **default anchor = today** for “every N days”.

[1]: https://core.telegram.org/bots/api "Telegram Bot API"
[2]: https://limits.tginfo.me/en "Telegram Limits — Telegram Info"

# Step-by-step implementation plan

# Step 1 — Bootstrap, Config, Docker (no comments/tests)

**PROMPT TO EXECUTE**

You are an agentic LLM implementing Step 1 of a Telegram scheduling bot.

## Project context (carry these through every step)

* One “batch session” starts with a user text message, proceeds via natural-language clarifications, then shows a **Proposed Task List** with inline buttons **✅ Approve** (`APR`) and **❌ Reject** (`REJ`).
* On Approve, return **up to 3** next run times per task.
* **UTC only** (`UTC`, +00:00). Weekends: Sat/Sun.
* `[work]` tasks shift forward off weekends/holidays; `[personal]` never shifts.
* Holidays are provided via **Telegram file attachment** named exactly `holidays.json` (MIME `application/json`, size ≤ 256 KB). Latest valid file during the session wins.
* No headers. No DSL. All clarifications and user inputs are natural language.
* No chunking: if outgoing text would exceed **4096 chars**, return `OUTPUT_TOO_LONG`. If incoming text exceeds the limit, return `INPUT_TOO_LONG`.
* One active session per chat; `/clear` ends and purges the session. `/help` explains usage.
* **Stateless across sessions**. Within a session, you may use all messages of that session only.
* LLM: GPT-5 via LangChain. Prompt budget guard: `MAX_PROMPT_TOKENS=24000` → if exceeded, `CONTEXT_TOO_LARGE`.
* No tests. No packaging. **No docstrings and no comments in code.**

## Deliverables

Create a minimal runnable scaffold (no product features yet):

```
/app
  /bot
    __init__.py
    main.py
    settings.py
    logging.py
    errors.py
  /infra
    __init__.py
    healthcheck.py
  requirements.txt
  Dockerfile
```

## Implementation requirements

* `settings.py`: read and validate envs: `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`, `APP_TZ=UTC` (hard-fail if not `UTC`), `LOG_LEVEL=INFO`, `MAX_PROMPT_TOKENS=24000`.
* `logging.py`: stdout logger (JSON or plain). Redact message bodies at INFO/WARN; allow full bodies only when `LOG_LEVEL=DEBUG`.
* `errors.py`: define string constants for:
  Per-task: `OK`, `NEED_TIME`, `NEED_TAG`, `UNSUPPORTED_RECURRENCE`, `NEED_ANCHOR`, `PARSE_FAILED`, `DROPPED_BY_USER`
  Batch: `NO_TASKS_FOUND`, `ATTACHMENT_MISSING`, `ATTACHMENT_INVALID`, `ATTACHMENT_MULTIPLE`, `ATTACHMENT_JSON_INVALID`, `HOLIDAYS_JSON_INVALID`, `INPUT_TOO_LONG`, `OUTPUT_TOO_LONG`, `CONTEXT_TOO_LARGE`, `SESSION_IN_PROGRESS`
* `main.py`: start aiogram app loop, log “ready”, handle SIGTERM gracefully.
* `healthcheck.py`: trivial OK output.
* `requirements.txt`: `aiogram`, `langchain`, `langchain-openai`, `python-dateutil`, `pydantic>=2`.
* `Dockerfile`: base `python:3.11-slim`, install deps, non-root user, `CMD ["python","-m","bot.main"]`.

## Acceptance

* Container builds and starts; logs confirm `APP_TZ=UTC` and “ready”.
* Startup hard-fails if required envs missing or `APP_TZ` ≠ `UTC`.

---

# Step 2 — LLM Contracts, Schemas, Holidays Parser (no comments/tests)

**PROMPT TO EXECUTE**

You are implementing Step 2: strict schemas, LLM prompts/chains with self-repair, and holidays file parsing. No Telegram handlers yet.

## Context (from Step 1 + core rules)

* Supported recurrences: `one_time`, `daily`, `weekday`, `weekly` (subset of days), `every_n_days` (N≥2).
* If `every_n_days` lacks an explicit start date, the anchor is **today** (UTC date of the session’s first user message).
* Missing time-of-day always triggers clarification.
* Classification: `[work]` vs `[personal]`. If uncertain, we will ask in natural language later.
* Prompt budget guard: `MAX_PROMPT_TOKENS=24000` → `CONTEXT_TOO_LARGE`.
* No tests. **No docstrings and no comments in code.**

## Deliverables

Create:

```
/bot/llm/__init__.py
/bot/llm/schemas.py
/bot/llm/prompts.py
/bot/llm/chain.py
/bot/holidays.py
```

## Implementation requirements

* `schemas.py` (Pydantic v2):

  * `TaskExtract` fields: `id:int`, `raw:str`, `name:str<=80`, `tag:Literal["work","personal","unsure"]`, `kind:Literal["one_time","daily","weekday","weekly","every_n_days"]`, `dow:list[str]` in `["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]`, `n_days:int>=2`, `date:"YYYY-MM-DD"` (for `one_time` or anchor), `time:"HH:MM"`, `needs:list[str]` subset of `["time","tag","unsupported","anchor"]`.
  * `TaskBatch` = list of `TaskExtract`.
  * `Holidays` with `version==1` and `dates[*].date` ISO `YYYY-MM-DD`.
* `prompts.py`:

  * **Extraction system prompt**: restate allowed patterns, forbid inventing details, require `needs` for missing items, output **strict JSON** compatible with `TaskBatch`.
  * **Self-repair prompt**: fix JSON to satisfy schema without changing meaning.
  * **Classification prompt**: assign `[work]` or `[personal]` only; if truly uncertain, return `unsure`.
* `chain.py`:

  * `extract_tasks(initial_text:str, session_messages:list[str], holidays:dict|None, now_utc:datetime, max_tokens:int) -> TaskBatch | "PARSE_FAILED" | "CONTEXT_TOO_LARGE"`

    * Compose context from all session messages since start (initial user text, bot clarifications, user replies) and the latest holidays JSON (pretty-printed). Enforce token guard.
    * Run extraction; if invalid JSON → run self-repair once; if still invalid → `PARSE_FAILED`.
  * `classify_tasks(batch:TaskBatch) -> TaskBatch` that fills `tag` when confidently classifiable; otherwise leave `unsure`.
* `holidays.py`:

  * `parse_telegram_document(name:str, mime:str, size:int, data:bytes) -> Holidays | error_code`
  * Enforce exact name `holidays.json`, MIME `application/json`, size ≤ 256 KB, schema validity.
  * Return specific error codes from the list.

## Acceptance

* Given messy multi-task text, `extract_tasks` yields normalized tasks with correct `needs`.
* Holidays parser accepts valid JSON and emits correct errors for invalid inputs.

---

# Step 3 — Scheduler (UTC) and Formatting (no comments/tests)

**PROMPT TO EXECUTE**

You are implementing Step 3: deterministic recurrence engine, workday/holiday shifting, and final date formatting.

## Context

* Timezone: **UTC** only. Ignore DST issues (not applicable in UTC).
* Weekends: Sat/Sun.
* `[work]` candidates falling on weekend/holiday must shift **forward** day-by-day to next non-holiday weekday; keep time.
* Skip any candidate `<= now`. Return next **up to 3**.
* Output format: `EEE, d MMM yyyy, HH:mm (UTC+00:00, UTC)`.
* No tests. **No docstrings and no comments in code.**

## Deliverables

Create:

```
/bot/scheduler/__init__.py
/bot/scheduler/rules.py
/bot/scheduler/engine.py
/bot/scheduler/format.py
```

## Implementation requirements

* `rules.py`: candidate generators using `dateutil.rrule` or equivalent:

  * `daily(HH:MM)`, `weekday(HH:MM)`, `weekly(dow_set, HH:MM)`, `every_n_days(interval, anchor_date, HH:MM)`, and `one_time(date, HH:MM)`.
* `engine.py`:

  * `next_occurrences(task:TaskExtract, now_utc:datetime, holidays:set[date]) -> list[datetime]`

    * Build candidates; skip `<= now`.
    * If task final tag is `[work]`, apply forward shift when needed.
    * Cap at 3.
* `format.py`: formatting helpers producing the exact final string representation.

## Acceptance

* For reference scenarios in the spec (weekday shift, holiday shift, “today at 09:00” when now is 14:00, `every_n_days` with default anchor), outputs match the described results.

---

# Step 4 — Telegram Wiring: Sessions, Clarifications, Inline Buttons, Final Output (no comments/tests)

**PROMPT TO EXECUTE**

You are implementing Step 4: complete aiogram integration, session lifecycle, holidays intake, clarifications in natural language, Proposed Task List, inline Approve/Reject, final schedule, and `/help` + `/clear`.

## Context

* One active session per chat; non-command messages join the current session until Approve/Reject or `/clear`.
* Session state is in-process only: initial user text, all session messages (for LLM context), latest valid holidays, current `TaskBatch`, and last proposal message id. Purge on end.
* Inline buttons: **✅ Approve** with `callback_data="APR"`, **❌ Reject** with `callback_data="REJ"`. Keep `callback_data` well under 64 bytes.
* Natural language only for the user.
* Enforce Telegram limits: incoming/outgoing text ≤ **4096** chars; otherwise `INPUT_TOO_LONG` or `OUTPUT_TOO_LONG`.
* If LLM context would exceed `MAX_PROMPT_TOKENS`, return `CONTEXT_TOO_LARGE`.
* No tests. **No docstrings and no comments in code.**

## Deliverables

Create:

```
/bot/telegram/__init__.py
/bot/telegram/app.py
/bot/telegram/session.py
/bot/telegram/templates.py
/bot/telegram/keyboards.py
```

Integrate these into `bot.main` startup.

## Implementation requirements

* `session.py`: in-memory store keyed by `chat_id` with fields for initial\_text, messages\[], latest\_holidays, task\_batch, last\_proposal\_msg\_id, created\_at. Helpers to start, get, append messages, and purge.
* `keyboards.py`: inline keyboard builder with the two buttons.
* `templates.py`:

  * Natural-language grouped clarification message builder.
  * Proposed Task List (names + recurrences, no dates).
  * Final SCHEDULE message using the scheduler’s `format.py`.
* `app.py` handlers:

  * `/help`: concise usage page with examples, supported recurrences, the `holidays.json` rule, UTC note.
  * `/clear`: purge session, reply “Session cleared.”
  * `document` handler: accept only `holidays.json`; parse with `holidays.py`; update session or reply with a plain-English error derived from error codes.
  * `message` handler (non-command text):

    * If no session: start session with this text; else append.
    * Build LLM context: all session messages + latest holidays JSON. If token guard triggers → reply with natural-language `CONTEXT_TOO_LARGE`.
    * Call `extract_tasks`; if `PARSE_FAILED` or no tasks → send a grouped, friendly clarification asking for restatement or specifics.
    * Call `classify_tasks`; if any tasks remain with `needs` (`time`, `tag`, `unsupported`, `anchor`): send a single grouped clarification in natural language.
    * If all tasks resolvable: render Proposed Task List and attach inline keyboard; store `last_proposal_msg_id`.
  * `callback_query` handler:

    * If `APR`: answer callback, edit proposal to “Approved ✅” and disable buttons; compute schedule using scheduler and holidays; if final string > 4096 → reply with `OUTPUT_TOO_LONG`; else send the final SCHEDULE; purge session.
    * If `REJ`: answer callback, edit proposal to “Rejected ❌” and disable buttons; purge session.

## Acceptance

* Happy path: user sends tasks → maybe clarifications → Proposed Task List with inline buttons → Approve → final SCHEDULE → session purged.
* Reject path: Proposed Task List → Reject → session purged.
* `/clear` ends any in-progress session immediately.
* Holidays apply only within the current session and only to `[work]` tasks.