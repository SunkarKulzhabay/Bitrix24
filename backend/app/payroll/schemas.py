from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.employees.schemas import EmployeeShort


# ---------- Что принимает API ----------
class SalaryUpdate(BaseModel):
    base_salary: Decimal = Field(ge=0, max_digits=14, decimal_places=2)


class EntryCreate(BaseModel):
    employee_id: int
    project_id: int
    work_date: date
    hours: Decimal = Field(default=0, ge=0, le=24, max_digits=6, decimal_places=2)
    amount: Decimal = Field(default=0, ge=0, max_digits=14, decimal_places=2)
    description: str = Field(default="", max_length=2000)


class KpiMetricCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    target_value: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    bonus_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    mode: Literal["proportional", "all_or_nothing"] = "proportional"


class KpiResultSet(BaseModel):
    employee_id: int
    metric_id: int
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    actual_value: Decimal = Field(ge=0, max_digits=14, decimal_places=2)


class PenaltyCreate(BaseModel):
    employee_id: int
    reason: str = Field(min_length=1, max_length=2000)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    issued_at: date | None = None


# ---------- Что отдаёт API ----------
class ProjectBrief(BaseModel):
    id: int
    name: str


class KpiMetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    target_value: float
    bonus_amount: float
    mode: str


class EntryOut(BaseModel):
    id: int
    work_date: date
    hours: float
    amount: float
    description: str


class ProjectEarnings(BaseModel):
    project_id: int
    project_name: str
    hours: float
    amount: float
    entries: list[EntryOut]


class KpiLine(BaseModel):
    metric_id: int
    name: str
    mode: str
    target_value: float
    actual_value: float
    max_bonus: float
    bonus: float


class PenaltyOut(BaseModel):
    id: int
    reason: str
    amount: float
    issued_at: date
    issued_by: str
    can_delete: bool = False


class PayrollOut(BaseModel):
    employee: EmployeeShort
    month: str
    base_salary: float
    projects_total: float
    kpi_total: float
    penalties_total: float
    total: float
    projects: list[ProjectEarnings]
    kpi: list[KpiLine]
    penalties: list[PenaltyOut]


class OverviewRow(BaseModel):
    employee: EmployeeShort
    base_salary: float
    projects_total: float
    kpi_total: float
    penalties_total: float
    total: float