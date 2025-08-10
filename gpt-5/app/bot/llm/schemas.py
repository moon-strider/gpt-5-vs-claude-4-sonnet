from typing import Literal, List, Optional
from pydantic import BaseModel, Field, ValidationInfo, field_validator, TypeAdapter
import re


ALLOWED_DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ALLOWED_NEEDS = ["time", "tag", "unsupported", "anchor"]


class TaskExtract(BaseModel):
    id: int
    raw: str
    name: str = Field(min_length=1, max_length=80)
    tag: Literal["work", "personal", "unsure"]
    kind: Literal["one_time", "daily", "weekday", "weekly", "every_n_days"]
    dow: List[str] = []
    n_days: Optional[int] = None
    date: Optional[str] = None
    time: Optional[str] = None
    needs: List[str] = []

    @field_validator("dow")
    def validate_dow(cls, v):
        for d in v:
            if d not in ALLOWED_DOW:
                raise ValueError("invalid day")
        return v

    @field_validator("n_days")
    def validate_n_days(cls, v):
        if v is None:
            return v
        if v < 2:
            raise ValueError("n_days must be >= 2")
        return v

    @field_validator("date")
    def validate_date(cls, v):
        if v is None:
            return v
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            raise ValueError("invalid date")
        return v

    @field_validator("time")
    def validate_time(cls, v):
        if v is None:
            return v
        if not re.fullmatch(r"\d{2}:\d{2}", v):
            raise ValueError("invalid time")
        hh, mm = v.split(":")
        if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
            raise ValueError("invalid time range")
        return v

    @field_validator("needs")
    def validate_needs(cls, v):
        for n in v:
            if n not in ALLOWED_NEEDS:
                raise ValueError("invalid need")
        return v


TaskBatch = TypeAdapter(list[TaskExtract])


class HolidayItem(BaseModel):
    date: str
    name: Optional[str] = None

    @field_validator("date")
    def validate_date(cls, v):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            raise ValueError("invalid date")
        return v


class Holidays(BaseModel):
    version: int
    dates: List[HolidayItem] = []

    @field_validator("version")
    def validate_version(cls, v):
        if v != 1:
            raise ValueError("version must be 1")
        return v

