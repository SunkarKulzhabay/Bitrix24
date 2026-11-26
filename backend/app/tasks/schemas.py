from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.employees.schemas import EmployeeShort

Priority = Literal[
    "urgent_important",
    "important_not_urgent",
    "urgent_not_important",
    "not_urgent_not_important",
]


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    priority: Priority = "important_not_urgent"
    deadline: datetime | None = None
    assignee_id: int
    supervisor_id: int | None = None


class StatusChange(BaseModel):
    status: Literal["in_progress", "in_review", "rework", "done"]


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: str
    priority: str
    deadline: datetime | None
    created_at: datetime
    creator: EmployeeShort
    assignee: EmployeeShort
    supervisor: EmployeeShort | None
    responsible: EmployeeShort
    # Какие статусы текущий пользователь может поставить этой задаче
    available_statuses: list[str] = []