from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.employees.schemas import EmployeeShort


class FieldDef(BaseModel):
    key: str
    label: str
    type: Literal["text", "date", "number", "textarea"]


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    fields: list[FieldDef]


class DocumentCreate(BaseModel):
    template_id: int
    values: dict[str, str] = {}
    with_stamp: bool = False


class SendRequest(BaseModel):
    approver_id: int


class DecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    comment: str = Field(default="", max_length=2000)


class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    approver: EmployeeShort
    status: str
    comment: str
    created_at: datetime
    decided_at: datetime | None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    number: str
    content: str
    with_stamp: bool
    status: str
    requester: EmployeeShort
    created_at: datetime
    approvals: list[ApprovalOut]
    stamp_text: str = ""
    can_send: bool = False
    can_decide: bool = False