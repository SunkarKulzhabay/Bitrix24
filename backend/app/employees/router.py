from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import date

from backend.app.auth.dependencies import require_roles, get_current_user
from backend.app.auth.security import hash_password
from backend.app.database import get_db
from backend.app.employees.models import Employee, StaffHistory
from backend.app.employees.schemas import (
    EmployeeCreate,
    EmployeeOut,
    EmployeeShort,
    EmployeeUpdate,
    PasswordChange,
)

router = APIRouter(prefix="/api/employees", tags=["employees"])

# Управлять сотрудниками могут администратор и HR
manage = require_roles("admin", "hr")


def only_admin_touches_admin(current: Employee, target_role: str) -> None:
    if target_role == "admin" and current.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Администраторов может менять только администратор")


async def get_or_404(db: AsyncSession, employee_id: int) -> Employee:
    employee = await db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Сотрудник не найден")
    return employee


@router.get("", response_model=list[EmployeeOut])
async def list_employees(db: AsyncSession = Depends(get_db), _: Employee = Depends(manage)):
    result = await db.execute(select(Employee).order_by(Employee.full_name))
    return result.scalars().all()


@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
async def create_employee(
    data: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    current: Employee = Depends(manage),
):
    only_admin_touches_admin(current, data.role)

    login = data.login.strip().lower()
    exists = await db.execute(select(Employee).where(Employee.login == login))
    if exists.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Такой логин уже занят")

    employee = Employee(
        full_name=data.full_name.strip(),
        login=login,
        password_hash=await run_in_threadpool(hash_password, data.password),
        role=data.role,
    )
    employee.hired_at = date.today()
    db.add(employee)
    await db.flush()
    db.add(
        StaffHistory(
            employee_id=employee.id,
            event_type="hired",
            event_date=date.today(),
            comment="Принят в компанию",
            created_by_id=current.id,
        )
    )
    await db.commit()
    await db.refresh(employee)
    return employee


@router.patch("/{employee_id}", response_model=EmployeeOut)
async def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    current: Employee = Depends(manage),
):
    employee = await get_or_404(db, employee_id)
    only_admin_touches_admin(current, employee.role)

    if data.role is not None:
        only_admin_touches_admin(current, data.role)

    if employee.id == current.id:
        if data.is_active is False or (data.role is not None and data.role != current.role):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Нельзя отключить себя или сменить свою роль")

    if data.full_name is not None:
        employee.full_name = data.full_name.strip()
    if data.role is not None:
        employee.role = data.role
    if data.is_active is not None:
        if data.is_active != employee.is_active:
            db.add(
                StaffHistory(
                    employee_id=employee.id,
                    event_type="rehired" if data.is_active else "fired",
                    event_date=date.today(),
                    comment="Принят повторно" if data.is_active else "Уволен (учётная запись отключена)",
                    created_by_id=current.id,
                )
            )
            employee.fired_at = None if data.is_active else date.today()
        employee.is_active = data.is_active

    await db.commit()
    await db.refresh(employee)
    return employee


@router.put("/{employee_id}/password", status_code=status.HTTP_204_NO_CONTENT)
async def set_password(
    employee_id: int,
    data: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current: Employee = Depends(manage),
):
    employee = await get_or_404(db, employee_id)
    only_admin_touches_admin(current, employee.role)

    employee.password_hash = await run_in_threadpool(hash_password, data.password)
    await db.commit()

@router.get("/directory", response_model=list[EmployeeShort])
async def directory(db: AsyncSession = Depends(get_db), _: Employee = Depends(get_current_user)):
    result = await db.execute(
        select(Employee).where(Employee.is_active.is_(True)).order_by(Employee.full_name)
    )
    return result.scalars().all()