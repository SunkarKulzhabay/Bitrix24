from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.employees.schemas import EmployeeShort


class NameCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class PositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str


class ChartNode(BaseModel):
    id: int
    full_name: str
    department_id: int | None
    department: str | None
    position_id: int | None
    position: str | None
    manager_id: int | None


class AssignmentUpdate(BaseModel):
    department_id: int | None
    position_id: int | None
    manager_id: int | None


class HistoryCreate(BaseModel):
    event_type: Literal["replaced", "moved_to_project", "note"]
    event_date: date | None = None
    comment: str = Field(default="", max_length=2000)
    related_employee_id: int | None = None


class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    event_date: date
    comment: str
    related_employee: EmployeeShort | None
    created_by: EmployeeShort
    created_at: datetime