from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import get_current_user, require_roles
from backend.app.database import get_db
from backend.app.employees.models import Department, Employee, Position, StaffHistory
from backend.app.org.schemas import (
    AssignmentUpdate,
    ChartNode,
    DepartmentOut,
    HistoryCreate,
    HistoryOut,
    NameCreate,
    PositionOut,
)

router = APIRouter(prefix="/api/org", tags=["org"])

manage = require_roles("admin", "hr")


def label(value: str | None) -> str:
    return value or "—"


def to_node(employee: Employee) -> ChartNode:
    return ChartNode(
        id=employee.id,
        full_name=employee.full_name,
        department_id=employee.department_id,
        department=employee.department.name if employee.department else None,
        position_id=employee.position_id,
        position=employee.position.title if employee.position else None,
        manager_id=employee.manager_id,
    )


async def fetch_employee(db: AsyncSession, employee_id: int) -> Employee | None:
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id).execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def creates_cycle(db: AsyncSession, employee_id: int, manager_id: int) -> bool:
    """Проверяет, что руководитель не окажется подчинённым самого себя."""
    seen: set[int] = set()
    current: int | None = manager_id
    while current is not None:
        if current == employee_id or current in seen:
            return True
        seen.add(current)
        manager = await db.get(Employee, current)
        current = manager.manager_id if manager else None
    return False


# ---------- Отделы ----------
@router.get("/departments", response_model=list[DepartmentOut])
async def list_departments(db: AsyncSession = Depends(get_db), _: Employee = Depends(get_current_user)):
    result = await db.execute(select(Department).order_by(Department.name))
    return result.scalars().all()


@router.post("/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
async def create_department(
    data: NameCreate, db: AsyncSession = Depends(get_db), _: Employee = Depends(manage)
):
    name = data.name.strip()
    exists = await db.scalar(select(Department.id).where(func.lower(Department.name) == name.lower()))
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Такой отдел уже есть")
    department = Department(name=name)
    db.add(department)
    await db.commit()
    await db.refresh(department)
    return department


@router.delete("/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    department_id: int, db: AsyncSession = Depends(get_db), _: Employee = Depends(manage)
):
    department = await db.get(Department, department_id)
    if department is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Отдел не найден")
    used = await db.scalar(
        select(func.count()).select_from(Employee).where(Employee.department_id == department_id)
    )
    if used:
        raise HTTPException(status.HTTP_409_CONFLICT, "В отделе есть сотрудники, сначала переведите их")
    await db.delete(department)
    await db.commit()


# ---------- Должности ----------
@router.get("/positions", response_model=list[PositionOut])
async def list_positions(db: AsyncSession = Depends(get_db), _: Employee = Depends(get_current_user)):
    result = await db.execute(select(Position).order_by(Position.title))
    return result.scalars().all()


@router.post("/positions", response_model=PositionOut, status_code=status.HTTP_201_CREATED)
async def create_position(
    data: NameCreate, db: AsyncSession = Depends(get_db), _: Employee = Depends(manage)
):
    title = data.name.strip()
    exists = await db.scalar(select(Position.id).where(func.lower(Position.title) == title.lower()))
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Такая должность уже есть")
    position = Position(title=title)
    db.add(position)
    await db.commit()
    await db.refresh(position)
    return position


@router.delete("/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(
    position_id: int, db: AsyncSession = Depends(get_db), _: Employee = Depends(manage)
):
    position = await db.get(Position, position_id)
    if position is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Должность не найдена")
    used = await db.scalar(
        select(func.count()).select_from(Employee).where(Employee.position_id == position_id)
    )
    if used:
        raise HTTPException(status.HTTP_409_CONFLICT, "Должность назначена сотрудникам")
    await db.delete(position)
    await db.commit()


# ---------- Схема ----------
@router.get("/chart", response_model=list[ChartNode])
async def chart(db: AsyncSession = Depends(get_db), _: Employee = Depends(get_current_user)):
    result = await db.execute(
        select(Employee).where(Employee.is_active.is_(True)).order_by(Employee.full_name)
    )
    return [to_node(employee) for employee in result.scalars().all()]


@router.put("/employees/{employee_id}/assignment", response_model=ChartNode)
async def set_assignment(
    employee_id: int,
    data: AssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(manage),
):
    employee = await fetch_employee(db, employee_id)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Сотрудник не найден")

    department = await db.get(Department, data.department_id) if data.department_id else None
    if data.department_id and department is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Отдел не найден")

    position = await db.get(Position, data.position_id) if data.position_id else None
    if data.position_id and position is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Должность не найдена")

    manager = None
    if data.manager_id:
        if data.manager_id == employee.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Сотрудник не может руководить собой")
        manager = await db.get(Employee, data.manager_id)
        if manager is None or not manager.is_active:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Руководитель не найден или отключён")
        if await creates_cycle(db, employee.id, data.manager_id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Так получится замкнутая цепочка подчинения")

    changes = []
    if employee.department_id != data.department_id:
        old = employee.department.name if employee.department else None
        changes.append(f"Отдел: {label(old)} → {label(department.name if department else None)}")
    if employee.position_id != data.position_id:
        old = employee.position.title if employee.position else None
        changes.append(f"Должность: {label(old)} → {label(position.title if position else None)}")
    if employee.manager_id != data.manager_id:
        old_manager = await db.get(Employee, employee.manager_id) if employee.manager_id else None
        changes.append(
            f"Руководитель: {label(old_manager.full_name if old_manager else None)}"
            f" → {label(manager.full_name if manager else None)}"
        )

    employee.department_id = data.department_id
    employee.position_id = data.position_id
    employee.manager_id = data.manager_id

    if changes:
        db.add(
            StaffHistory(
                employee_id=employee.id,
                event_type="transferred",
                event_date=date.today(),
                comment="; ".join(changes),
                created_by_id=user.id,
            )
        )
    await db.commit()

    return to_node(await fetch_employee(db, employee_id))


# ---------- История кадров ----------
@router.get("/history/{employee_id}", response_model=list[HistoryOut])
async def get_history(
    employee_id: int, db: AsyncSession = Depends(get_db), user: Employee = Depends(get_current_user)
):
    if user.id != employee_id and user.role not in ("admin", "hr"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
    result = await db.execute(
        select(StaffHistory)
        .where(StaffHistory.employee_id == employee_id)
        .order_by(StaffHistory.event_date.desc(), StaffHistory.id.desc())
    )
    return result.scalars().all()


@router.post("/history/{employee_id}", response_model=HistoryOut, status_code=status.HTTP_201_CREATED)
async def add_history(
    employee_id: int,
    data: HistoryCreate,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(manage),
):
    if await db.get(Employee, employee_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Сотрудник не найден")

    if data.event_type == "replaced" and not data.related_employee_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Укажите, кем заменён сотрудник")
    if data.event_type != "replaced" and not data.comment.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Добавьте комментарий")
    if data.related_employee_id and await db.get(Employee, data.related_employee_id) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Сотрудник не найден")

    entry = StaffHistory(
        employee_id=employee_id,
        event_type=data.event_type,
        event_date=data.event_date or date.today(),
        comment=data.comment.strip(),
        related_employee_id=data.related_employee_id,
        created_by_id=user.id,
    )
    db.add(entry)
    await db.commit()

    result = await db.execute(
        select(StaffHistory)
        .where(StaffHistory.id == entry.id)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one()