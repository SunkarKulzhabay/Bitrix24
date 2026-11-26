from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    kind: Literal["meeting", "assembly"] = "meeting"
    starts_at: datetime
    ends_at: datetime
    place: str = Field(default="", max_length=200)
    participant_ids: list[int] = []


class CalendarItem(BaseModel):
    kind: Literal["task", "meeting", "assembly"]
    id: int
    title: str
    description: str = ""
    starts_at: datetime
    ends_at: datetime | None = None
    place: str = ""
    organizer: str | None = None
    participants: list[str] = []
    status: str | None = None
    can_delete: bool = False