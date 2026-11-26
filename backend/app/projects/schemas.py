from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.employees.schemas import EmployeeShort

Stage = Literal[
    "new",
    "pilot_prep",
    "pilot_running",
    "avr_report",
    "contract_review",
    "presentation_payment",
    "contract_talks",
    "done",
    "paused",
    "refused",
]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    partner_name: str = Field(min_length=1, max_length=200)
    contact_person: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=50)
    services: str = Field(default="", max_length=5000)
    deal_amount: Decimal = Field(default=0, ge=0, max_digits=14, decimal_places=2)
    curator_id: int | None = None


class StageRequest(BaseModel):
    stage: Stage
    reason: str = Field(default="", max_length=2000)


class MemberCreate(BaseModel):
    employee_id: int
    role: str = Field(min_length=1, max_length=100)
    reports_to_id: int | None = None


class PartnerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_name: str
    contact_person: str
    phone: str


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee: EmployeeShort
    role: str
    reports_to_id: int | None


class StageChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_stage: str
    to_stage: str
    changed_by: EmployeeShort
    changed_at: datetime
    comment: str


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    partner: PartnerOut
    services: str
    deal_amount: float
    stage: str
    refusal_reason: str
    curator: EmployeeShort
    created_at: datetime
    members: list[MemberOut]
    history: list[StageChangeOut]
    can_manage: bool = False