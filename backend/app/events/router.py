from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import get_current_user
from backend.app.database import get_db
from backend.app.employees.models import Employee
from backend.app.events.models import CalendarEvent, EventParticipant
from backend.app.events.schemas import CalendarItem, EventCreate
from backend.app.tasks.models import Task

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


def event_to_item(event: CalendarEvent, user: Employee) -> CalendarItem:
    return CalendarItem(
        kind=event.kind,
        id=event.id,
        title=event.title,
        description=event.description,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        place=event.place,
        organizer=event.organizer.full_name,
        participants=[p.employee.full_name for p in event.participants],
        can_delete=(user.id == event.organizer_id or user.role == "admin"),
    )


def task_to_item(task: Task) -> CalendarItem:
    return CalendarItem(
        kind="task",
        id=task.id,
        title=task.title,
        description=task.description,
        starts_at=task.deadline,
        status=task.status,
    )


@router.get("", response_model=list[CalendarItem])
async def get_calendar(
    start: datetime,
    end: datetime,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    start = start.replace(tzinfo=None)
    end = end.replace(tzinfo=None)

    events_result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.starts_at >= start,
            CalendarEvent.starts_at < end,
            or_(
                CalendarEvent.organizer_id == user.id,
                CalendarEvent.participants.any(EventParticipant.employee_id == user.id),
            ),
        )
    )
    tasks_result = await db.execute(
        select(Task).where(
            Task.deadline >= start,
            Task.deadline < end,
            or_(
                Task.creator_id == user.id,
                Task.assignee_id == user.id,
                Task.supervisor_id == user.id,
            ),
        )
    )

    items = [event_to_item(e, user) for e in events_result.scalars().unique().all()]
    items += [task_to_item(t) for t in tasks_result.scalars().unique().all()]
    items.sort(key=lambda item: item.starts_at)
    return items


@router.post("/events", response_model=CalendarItem, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: EventCreate,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    starts_at = data.starts_at.replace(tzinfo=None)
    ends_at = data.ends_at.replace(tzinfo=None)
    if ends_at <= starts_at:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Время окончания должно быть позже начала")

    participant_ids = {i for i in data.participant_ids if i != user.id}
    if participant_ids:
        found = await db.execute(
            select(Employee.id).where(
                Employee.id.in_(participant_ids), Employee.is_active.is_(True)
            )
        )
        if len(found.scalars().all()) != len(participant_ids):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Участник не найден или отключён")

    event = CalendarEvent(
        title=data.title.strip(),
        description=data.description.strip(),
        kind=data.kind,
        starts_at=starts_at,
        ends_at=ends_at,
        place=data.place.strip(),
        organizer_id=user.id,
        participants=[EventParticipant(employee_id=i) for i in participant_ids],
    )
    db.add(event)
    await db.commit()
    event_id = event.id

    db.expunge_all()
    result = await db.execute(select(CalendarEvent).where(CalendarEvent.id == event_id))
    return event_to_item(result.scalar_one(), user)


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    event = await db.get(CalendarEvent, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Событие не найдено")
    if user.id != event.organizer_id and user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Удалить может только организатор")

    await db.delete(event)
    await db.commit()