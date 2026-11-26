from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base
from backend.app.employees.models import Employee


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(20), default="meeting")  # meeting или assembly
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    place: Mapped[str] = mapped_column(String(200), default="")
    organizer_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))

    organizer: Mapped[Employee] = relationship(lazy="joined")
    participants: Mapped[list["EventParticipant"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class EventParticipant(Base):
    __tablename__ = "event_participants"

    event_id: Mapped[int] = mapped_column(
        ForeignKey("calendar_events.id", ondelete="CASCADE"), primary_key=True
    )
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), primary_key=True)

    employee: Mapped[Employee] = relationship(lazy="joined")