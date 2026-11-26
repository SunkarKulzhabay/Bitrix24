from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import get_current_user, require_roles
from backend.app.database import get_db
from backend.app.employees.models import Employee
from backend.app.payroll.models import (
    KpiMetric,
    KpiResult,
    Penalty,
    SalarySetting,
    TimesheetEntry,
)
from backend.app.payroll.schemas import (
    EntryCreate,
    KpiMetricCreate,
    KpiMetricOut,
    KpiResultSet,
    OverviewRow,
    PayrollOut,
    PenaltyCreate,
    ProjectBrief,
    SalaryUpdate,
)
from backend.app.payroll.service import build_payroll, parse_month
from backend.app.projects.models import Project

router = APIRouter(prefix="/api/payroll", tags=["payroll"])

finance = require_roles("admin", "accountant")
fine_givers = require_roles("admin", "manager")


async def active_employee(db: AsyncSession, employee_id: int) -> Employee:
    employee = await db.get(Employee, employee_id)
    if employee is None or not employee.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Сотрудник не найден или отключён")
    return employee


@router.get("/summary", response_model=PayrollOut)
async def summary(
    month: str,
    employee_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    start, end = parse_month(month)
    target = user
    if employee_id is not None and employee_id != user.id:
        if user.role not in ("admin", "accountant"):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
        target = await db.get(Employee, employee_id)
        if target is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Сотрудник не найден")
    return await build_payroll(db, target, start, end, user)


@router.get("/overview", response_model=list[OverviewRow])
async def overview(
    month: str, db: AsyncSession = Depends(get_db), user: Employee = Depends(finance)
):
    start, end = parse_month(month)
    result = await db.execute(
        select(Employee).where(Employee.is_active.is_(True)).order_by(Employee.full_name)
    )
    rows = []
    for employee in result.scalars().all():
        payroll = await build_payroll(db, employee, start, end, user)
        rows.append(
            OverviewRow(
                employee=payroll.employee,
                base_salary=payroll.base_salary,
                projects_total=payroll.projects_total,
                kpi_total=payroll.kpi_total,
                penalties_total=payroll.penalties_total,
                total=payroll.total,
            )
        )
    return rows


@router.get("/projects", response_model=list[ProjectBrief])
async def all_projects(db: AsyncSession = Depends(get_db), _: Employee = Depends(finance)):
    result = await db.execute(select(Project).order_by(Project.name))
    return [ProjectBrief(id=project.id, name=project.name) for project in result.scalars().all()]


@router.put("/salary/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def set_salary(
    employee_id: int,
    data: SalaryUpdate,
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(finance),
):
    await active_employee(db, employee_id)
    salary = await db.get(SalarySetting, employee_id)
    if salary:
        salary.base_salary = data.base_salary
    else:
        db.add(SalarySetting(employee_id=employee_id, base_salary=data.base_salary))
    await db.commit()


@router.post("/entries", status_code=status.HTTP_201_CREATED)
async def create_entry(
    data: EntryCreate,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(finance),
):
    await active_employee(db, data.employee_id)
    if await db.get(Project, data.project_id) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Проект не найден")

    entry = TimesheetEntry(
        employee_id=data.employee_id,
        project_id=data.project_id,
        work_date=data.work_date,
        hours=data.hours,
        amount=data.amount,
        description=data.description.strip(),
        created_by_id=user.id,
    )
    db.add(entry)
    await db.commit()
    return {"id": entry.id}


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: int, db: AsyncSession = Depends(get_db), _: Employee = Depends(finance)
):
    entry = await db.get(TimesheetEntry, entry_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Запись не найдена")
    await db.delete(entry)
    await db.commit()


@router.get("/kpi/metrics", response_model=list[KpiMetricOut])
async def list_metrics(db: AsyncSession = Depends(get_db), _: Employee = Depends(finance)):
    result = await db.execute(
        select(KpiMetric).where(KpiMetric.is_active.is_(True)).order_by(KpiMetric.name)
    )
    return result.scalars().all()


@router.post("/kpi/metrics", response_model=KpiMetricOut, status_code=status.HTTP_201_CREATED)
async def create_metric(
    data: KpiMetricCreate, db: AsyncSession = Depends(get_db), _: Employee = Depends(finance)
):
    metric = KpiMetric(
        name=data.name.strip(),
        target_value=data.target_value,
        bonus_amount=data.bonus_amount,
        mode=data.mode,
    )
    db.add(metric)
    await db.commit()
    await db.refresh(metric)
    return metric


@router.delete("/kpi/metrics/{metric_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_metric(
    metric_id: int, db: AsyncSession = Depends(get_db), _: Employee = Depends(finance)
):
    metric = await db.get(KpiMetric, metric_id)
    if metric is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Метрика не найдена")
    # Не удаляем, чтобы не потерять уже посчитанные месяцы
    metric.is_active = False
    await db.commit()


@router.put("/kpi/results", status_code=status.HTTP_204_NO_CONTENT)
async def set_result(
    data: KpiResultSet, db: AsyncSession = Depends(get_db), _: Employee = Depends(finance)
):
    start, _end = parse_month(data.month)
    await active_employee(db, data.employee_id)
    metric = await db.get(KpiMetric, data.metric_id)
    if metric is None or not metric.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Метрика не найдена")

    found = await db.execute(
        select(KpiResult).where(
            KpiResult.employee_id == data.employee_id,
            KpiResult.metric_id == data.metric_id,
            KpiResult.month == start,
        )
    )
    row = found.scalar_one_or_none()
    if row:
        row.actual_value = data.actual_value
    else:
        db.add(
            KpiResult(
                employee_id=data.employee_id,
                metric_id=data.metric_id,
                month=start,
                actual_value=data.actual_value,
            )
        )
    await db.commit()


@router.post("/penalties", status_code=status.HTTP_201_CREATED)
async def create_penalty(
    data: PenaltyCreate,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(fine_givers),
):
    await active_employee(db, data.employee_id)
    penalty = Penalty(
        employee_id=data.employee_id,
        reason=data.reason.strip(),
        amount=data.amount,
        issued_at=data.issued_at or date.today(),
        issued_by_id=user.id,
    )
    db.add(penalty)
    await db.commit()
    return {"id": penalty.id}


@router.delete("/penalties/{penalty_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_penalty(
    penalty_id: int,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    penalty = await db.get(Penalty, penalty_id)
    if penalty is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Штраф не найден")
    if user.role != "admin" and penalty.issued_by_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Удалить штраф может тот, кто его выдал, или администратор")
    await db.delete(penalty)
    await db.commit()