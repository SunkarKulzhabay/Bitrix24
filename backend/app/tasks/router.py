from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import get_current_user
from backend.app.database import get_db
from backend.app.employees.models import Employee
from backend.app.tasks.models import Task
from backend.app.tasks.schemas import StatusChange, TaskCreate, TaskOut

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# Из какого статуса в какой можно перейти и кто это делает
TRANSITIONS = {
    "pending": {"in_progress": "worker"},
    "in_progress": {"in_review": "worker"},
    "in_review": {"done": "creator", "rework": "creator"},
    "rework": {"in_review": "worker"},
}


def available_statuses(task: Task, user: Employee) -> list[str]:
    is_worker = user.id in (task.assignee_id, task.supervisor_id)
    is_creator = user.id == task.creator_id
    result = []
    for new_status, who in TRANSITIONS.get(task.status, {}).items():
        if (who == "worker" and is_worker) or (who == "creator" and is_creator):
            result.append(new_status)
    return result


def to_out(task: Task, user: Employee) -> TaskOut:
    out = TaskOut.model_validate(task)
    out.available_statuses = available_statuses(task, user)
    return out


async def load_task(db: AsyncSession, task_id: int) -> Task:
    result = await db.execute(
        select(Task).where(Task.id == task_id).execution_options(populate_existing=True)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Задача не найдена")
    return task


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    view: Literal["assigned", "created", "all"] = "all",
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    if view == "assigned":
        condition = or_(Task.assignee_id == user.id, Task.supervisor_id == user.id)
    elif view == "created":
        condition = Task.creator_id == user.id
    else:
        condition = or_(
            Task.creator_id == user.id,
            Task.assignee_id == user.id,
            Task.supervisor_id == user.id,
        )

    result = await db.execute(
        select(Task).where(condition).order_by(Task.deadline.asc().nulls_last(), Task.id.desc())
    )
    return [to_out(task, user) for task in result.scalars().all()]


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    for employee_id in (data.assignee_id, data.supervisor_id):
        if employee_id is None:
            continue
        employee = await db.get(Employee, employee_id)
        if employee is None or not employee.is_active:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Сотрудник не найден или отключён")

    deadline = data.deadline.replace(tzinfo=None) if data.deadline else None

    task = Task(
        title=data.title.strip(),
        description=data.description.strip(),
        priority=data.priority,
        deadline=deadline,
        creator_id=user.id,
        assignee_id=data.assignee_id,
        supervisor_id=data.supervisor_id,
    )
    db.add(task)
    await db.commit()

    task = await load_task(db, task.id)
    return to_out(task, user)


@router.post("/{task_id}/status", response_model=TaskOut)
async def change_status(
    task_id: int,
    data: StatusChange,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    task = await load_task(db, task_id)
    if data.status not in available_statuses(task, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нельзя перевести задачу в этот статус")

    task.status = data.status
    await db.commit()

    task = await load_task(db, task_id)
    return to_out(task, user)