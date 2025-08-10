import json
from typing import Any
from .errors import (
    ATTACHMENT_INVALID,
    ATTACHMENT_JSON_INVALID,
    HOLIDAYS_JSON_INVALID,
)
from .llm.schemas import Holidays
from pydantic import ValidationError


def parse_telegram_document(name: str, mime: str, size: int, data: bytes):
    if name != "holidays.json":
        return ATTACHMENT_INVALID
    if mime != "application/json":
        return ATTACHMENT_INVALID
    if size > 256 * 1024:
        return ATTACHMENT_INVALID
    try:
        obj = json.loads(data.decode("utf-8"))
    except Exception:
        return ATTACHMENT_JSON_INVALID
    try:
        h = Holidays(**obj)
        return h
    except ValidationError:
        return HOLIDAYS_JSON_INVALID

