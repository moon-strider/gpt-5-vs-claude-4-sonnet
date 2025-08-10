import json
from datetime import datetime
from typing import Any, Dict, List, Tuple
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from pydantic import ValidationError
from .schemas import TaskExtract, TaskBatch
from .prompts import EXTRACTION_SYSTEM, SELF_REPAIR_SYSTEM, CLASSIFY_SYSTEM


def _approx_tokens(s: str) -> int:
    return max(1, len(s) // 4)


def _extract_json_array(text: str) -> str:
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def extract_tasks(initial_text: str, session_messages: List[str], holidays: Dict[str, Any] | None, now_utc: datetime, max_tokens: int):
    context_parts = [initial_text] + session_messages
    if holidays is not None:
        try:
            context_parts.append(json.dumps(holidays, indent=2))
        except Exception:
            pass
    ctx = "\n\n".join(context_parts)
    if _approx_tokens(ctx) > max_tokens:
        return "CONTEXT_TOO_LARGE"

    model = ChatOpenAI(model="gpt-5", temperature=0)
    messages = [
        SystemMessage(content=EXTRACTION_SYSTEM),
        HumanMessage(content=f"Now(UTC): {now_utc.isoformat()}\n\nInput:\n{ctx}\n\nReturn only JSON array."),
    ]
    result = model.invoke(messages)
    text = _extract_json_array(result.content)
    try:
        data = json.loads(text)
        batch = TaskBatch.validate_python(data)
        return batch
    except Exception as e:
        repair_model = ChatOpenAI(model="gpt-5", temperature=0)
        repair_messages = [
            SystemMessage(content=SELF_REPAIR_SYSTEM),
            HumanMessage(content=f"Error: {str(e)}\n\nJSON to fix:\n{text}"),
        ]
        repair = repair_model.invoke(repair_messages)
        fixed = _extract_json_array(repair.content)
        try:
            data = json.loads(fixed)
            batch = TaskBatch.validate_python(data)
            return batch
        except Exception:
            return "PARSE_FAILED"


def classify_tasks(batch: List[TaskExtract]) -> List[TaskExtract]:
    items = [{"id": t.id, "name": t.name, "raw": t.raw} for t in batch]
    model = ChatOpenAI(model="gpt-5", temperature=0)
    messages = [
        SystemMessage(content=CLASSIFY_SYSTEM),
        HumanMessage(content=json.dumps(items)),
    ]
    result = model.invoke(messages)
    try:
        arr = json.loads(_extract_json_array(result.content))
    except Exception:
        return batch
    mapping = {}
    for e in arr:
        try:
            i = int(e.get("id"))
            tag = e.get("tag")
            if tag in ("work", "personal", "unsure"):
                mapping[i] = tag
        except Exception:
            pass
    out = []
    for t in batch:
        tag = mapping.get(t.id, t.tag)
        out.append(TaskExtract(**{**t.model_dump(), "tag": tag}))
    return out

