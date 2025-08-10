import io
import json
from datetime import datetime, timezone, date
from typing import List
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram import types
from ..settings import Settings
from ..logging import redact_text
from ..errors import (
    INPUT_TOO_LONG,
    OUTPUT_TOO_LONG,
    CONTEXT_TOO_LARGE,
    ATTACHMENT_INVALID,
    ATTACHMENT_JSON_INVALID,
    HOLIDAYS_JSON_INVALID,
)
from ..llm.chain import extract_tasks, classify_tasks
from ..llm.schemas import TaskExtract, Holidays
from ..holidays import parse_telegram_document
from .session import SessionStore
from .keyboards import approval_keyboard, disabled_keyboard
from .templates import build_clarifications, build_proposed_list, build_final_schedule


store = SessionStore()


def create_router(settings: Settings) -> Router:
    r = Router()

    @r.message(Command("help"))
    async def help_cmd(message: Message):
        text = (
            "I can parse your natural-language tasks and propose a schedule.\n\n"
            "Examples:\n"
            "- Pay invoices every weekday at 09:00 [work]\n"
            "- Gym on Mon and Wed at 19:00 [personal]\n"
            "- Every 3 days at 07:30 starting 2025-08-09\n\n"
            "Attach one file named holidays.json (application/json, ≤ 256 KB) to include holidays.\n"
            "Timezone: UTC only. After I show the Proposed Task List, use the inline buttons: ✅ Approve or ❌ Reject. Use /clear to start over."
        )
        await message.answer(text)

    @r.message(Command("clear"))
    async def clear_cmd(message: Message):
        if message.chat:
            store.purge(message.chat.id)
        await message.answer("Session cleared.")

    @r.message(F.document)
    async def on_document(message: Message):
        if not message.chat:
            return
        if message.media_group_id:
            await message.answer("ATTACHMENT_MULTIPLE")
            return
        doc = message.document
        if not doc:
            await message.answer("ATTACHMENT_MISSING")
            return
        bot = message.bot
        bio = io.BytesIO()
        await bot.download(doc, destination=bio)
        data = bio.getvalue()
        parsed = parse_telegram_document(doc.file_name or "", doc.mime_type or "", doc.file_size or 0, data)
        if isinstance(parsed, str):
            if parsed == ATTACHMENT_JSON_INVALID:
                await message.answer("ATTACHMENT_JSON_INVALID")
            elif parsed == HOLIDAYS_JSON_INVALID:
                await message.answer("HOLIDAYS_JSON_INVALID")
            else:
                await message.answer("ATTACHMENT_INVALID")
            return
        s = store.get(message.chat.id)
        if not s:
            s = store.start(message.chat.id, "", datetime.now(timezone.utc))
        store.set_holidays(message.chat.id, parsed)
        await message.answer("Holidays updated for this session.")

    @r.message(F.text & ~F.via_bot & ~F.text.startswith("/"))
    async def on_text(message: Message):
        if not message.chat:
            return
        chat_id = message.chat.id
        txt = message.text or ""
        if len(txt) > 4096:
            await message.answer(INPUT_TOO_LONG)
            return
        now = message.date or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        s = store.get(chat_id)
        if not s:
            s = store.start(chat_id, txt, now)
        else:
            store.append_message(chat_id, txt)
        holidays_obj = s.latest_holidays.model_dump() if s.latest_holidays else None
        res = extract_tasks(s.initial_text, s.messages, holidays_obj, now, settings.MAX_PROMPT_TOKENS)
        if res == CONTEXT_TOO_LARGE:
            await message.answer(CONTEXT_TOO_LARGE)
            return
        if res == "PARSE_FAILED":
            await message.answer("I couldn't parse that. Please restate each task and include times like HH:MM.")
            return
        batch = res
        if not batch or len(batch) == 0:
            await message.answer("NO_TASKS_FOUND")
            return
        batch2 = classify_tasks(batch)
        unresolved = []
        for t in batch2:
            needs = list(t.needs or [])
            if t.tag == "unsure" and "tag" not in needs:
                needs.append("tag")
            if needs:
                unresolved.append(t)
        if unresolved:
            msg = build_clarifications(batch2)
            if len(msg) > 4096:
                await message.answer(OUTPUT_TOO_LONG)
                return
            await message.answer(msg)
            store.append_message(chat_id, msg)
            store.set_task_batch(chat_id, batch2)
            return
        proposal = build_proposed_list(batch2)
        if len(proposal) > 4096:
            await message.answer(OUTPUT_TOO_LONG)
            return
        sent = await message.answer(proposal, reply_markup=approval_keyboard())
        store.set_task_batch(chat_id, batch2)
        store.set_last_proposal(chat_id, sent.message_id)

    @r.callback_query(F.data == "APR")
    async def on_approve(cb: CallbackQuery):
        await cb.answer()
        if not cb.message or not cb.message.chat:
            return
        chat_id = cb.message.chat.id
        s = store.get(chat_id)
        if not s or not s.task_batch:
            return
        try:
            await cb.message.edit_text("Approved ✅", reply_markup=disabled_keyboard())
        except Exception:
            pass
        now = datetime.now(timezone.utc)
        holidays_list: List[date] = []
        if s.latest_holidays:
            for d in s.latest_holidays.dates:
                y, m, d2 = [int(x) for x in d.date.split("-")]
                holidays_list.append(date(y, m, d2))
        final = build_final_schedule(s.task_batch, now, holidays_list, s.created_at.date())
        if len(final) > 4096:
            await cb.message.answer(OUTPUT_TOO_LONG)
        else:
            await cb.message.answer(final)
        store.purge(chat_id)

    @r.callback_query(F.data == "REJ")
    async def on_reject(cb: CallbackQuery):
        await cb.answer()
        if not cb.message or not cb.message.chat:
            return
        try:
            await cb.message.edit_text("Rejected ❌", reply_markup=disabled_keyboard())
        except Exception:
            pass
        store.purge(cb.message.chat.id)

    return r
