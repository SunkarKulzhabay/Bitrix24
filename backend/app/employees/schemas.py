from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["admin", "manager", "hr", "accountant", "employee"]


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    login: str
    role: str
    is_active: bool


class EmployeeCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    login: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    role: Role = "employee"


class EmployeeUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    role: Role | None = None
    is_active: bool | None = None


class PasswordChange(BaseModel):
    password: str = Field(min_length=8, max_length=128)

class EmployeeShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str