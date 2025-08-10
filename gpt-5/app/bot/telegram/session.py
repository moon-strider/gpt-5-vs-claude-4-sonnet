from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel
from ..llm.schemas import Holidays, TaskExtract


class Session(BaseModel):
    initial_text: str
    messages: List[str]
    latest_holidays: Optional[Holidays] = None
    task_batch: Optional[List[TaskExtract]] = None
    last_proposal_msg_id: Optional[int] = None
    created_at: datetime


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[int, Session] = {}

    def start(self, chat_id: int, initial_text: str, now: datetime) -> Session:
        s = Session(initial_text=initial_text, messages=[], created_at=now)
        self._sessions[chat_id] = s
        return s

    def get(self, chat_id: int) -> Optional[Session]:
        return self._sessions.get(chat_id)

    def append_message(self, chat_id: int, text: str) -> None:
        s = self._sessions.get(chat_id)
        if s is not None:
            s.messages.append(text)

    def set_holidays(self, chat_id: int, holidays: Holidays) -> None:
        s = self._sessions.get(chat_id)
        if s is not None:
            s.latest_holidays = holidays

    def set_task_batch(self, chat_id: int, batch: List[TaskExtract]) -> None:
        s = self._sessions.get(chat_id)
        if s is not None:
            s.task_batch = batch

    def set_last_proposal(self, chat_id: int, message_id: int) -> None:
        s = self._sessions.get(chat_id)
        if s is not None:
            s.last_proposal_msg_id = message_id

    def purge(self, chat_id: int) -> None:
        if chat_id in self._sessions:
            del self._sessions[chat_id]

