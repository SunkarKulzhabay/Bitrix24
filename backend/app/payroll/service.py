from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.employees.models import Employee
from backend.app.employees.schemas import EmployeeShort
from backend.app.payroll.models import KpiResult, Penalty, SalarySetting, TimesheetEntry
from backend.app.payroll.schemas import (
    EntryOut,
    KpiLine,
    PayrollOut,
    PenaltyOut,
    ProjectEarnings,
)

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def parse_month(value: str) -> tuple[date, date]:
    """'2026-11' -> (1 ноября, 1 декабря)"""
    try:
        year, month = value.split("-")
        start = date(int(year), int(month), 1)
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Месяц нужен в формате ГГГГ-ММ")
    end = date(start.year + (1 if start.month == 12 else 0), start.month % 12 + 1, 1)
    return start, end


def kpi_bonus(mode: str, target: Decimal, bonus: Decimal, actual: Decimal) -> Decimal:
    if target <= 0:
        return ZERO
    if mode == "all_or_nothing":
        return money(bonus) if actual >= target else ZERO
    ratio = min(actual / target, Decimal(1))
    return money(bonus * ratio)


async def build_payroll(
    db: AsyncSession, employee: Employee, start: date, end: date, viewer: Employee
) -> PayrollOut:
    # Оклад
    salary = await db.get(SalarySetting, employee.id)
    base = money(salary.base_salary) if salary else ZERO

    # Табель: записи по проектам
    entries = (
        (
            await db.execute(
                select(TimesheetEntry)
                .where(
                    TimesheetEntry.employee_id == employee.id,
                    TimesheetEntry.work_date >= start,
                    TimesheetEntry.work_date < end,
                )
                .order_by(TimesheetEntry.work_date, TimesheetEntry.id)
            )
        )
        .scalars()
        .unique()
        .all()
    )

    groups: dict[int, dict] = {}
    for entry in entries:
        group = groups.setdefault(
            entry.project_id,
            {"name": entry.project.name, "hours": ZERO, "amount": ZERO, "entries": []},
        )
        group["hours"] += entry.hours
        group["amount"] += entry.amount
        group["entries"].append(
            EntryOut(
                id=entry.id,
                work_date=entry.work_date,
                hours=float(entry.hours),
                amount=float(entry.amount),
                description=entry.description,
            )
        )

    projects = [
        ProjectEarnings(
            project_id=project_id,
            project_name=group["name"],
            hours=float(group["hours"]),
            amount=float(group["amount"]),
            entries=group["entries"],
        )
        for project_id, group in groups.items()
    ]
    projects_total = sum((group["amount"] for group in groups.values()), ZERO)

    # KPI
    results = (
        (
            await db.execute(
                select(KpiResult).where(
                    KpiResult.employee_id == employee.id, KpiResult.month == start
                )
            )
        )
        .scalars()
        .unique()
        .all()
    )
    kpi_lines = []
    kpi_total = ZERO
    for result in results:
        metric = result.metric
        bonus = kpi_bonus(metric.mode, metric.target_value, metric.bonus_amount, result.actual_value)
        kpi_total += bonus
        kpi_lines.append(
            KpiLine(
                metric_id=metric.id,
                name=metric.name,
                mode=metric.mode,
                target_value=float(metric.target_value),
                actual_value=float(result.actual_value),
                max_bonus=float(metric.bonus_amount),
                bonus=float(bonus),
            )
        )

    # Штрафы
    penalties = (
        (
            await db.execute(
                select(Penalty)
                .where(
                    Penalty.employee_id == employee.id,
                    Penalty.issued_at >= start,
                    Penalty.issued_at < end,
                )
                .order_by(Penalty.issued_at, Penalty.id)
            )
        )
        .scalars()
        .unique()
        .all()
    )
    penalties_total = sum((penalty.amount for penalty in penalties), ZERO)
    penalty_lines = [
        PenaltyOut(
            id=penalty.id,
            reason=penalty.reason,
            amount=float(penalty.amount),
            issued_at=penalty.issued_at,
            issued_by=penalty.issued_by.full_name,
            can_delete=viewer.role == "admin" or penalty.issued_by_id == viewer.id,
        )
        for penalty in penalties
    ]

    total = base + projects_total + kpi_total - penalties_total

    return PayrollOut(
        employee=EmployeeShort.model_validate(employee),
        month=start.strftime("%Y-%m"),
        base_salary=float(base),
        projects_total=float(projects_total),
        kpi_total=float(kpi_total),
        penalties_total=float(penalties_total),
        total=float(total),
        projects=projects,
        kpi=kpi_lines,
        penalties=penalty_lines,
    )