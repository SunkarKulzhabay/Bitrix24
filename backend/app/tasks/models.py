from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base
from backend.app.employees.models import Employee


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    priority: Mapped[str] = mapped_column(String(30), default="important_not_urgent")
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    creator_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    assignee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    supervisor_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)

    creator: Mapped[Employee] = relationship(foreign_keys=[creator_id], lazy="joined")
    assignee: Mapped[Employee] = relationship(foreign_keys=[assignee_id], lazy="joined")
    supervisor: Mapped[Employee | None] = relationship(foreign_keys=[supervisor_id], lazy="joined")

    @property
    def responsible(self) -> Employee:
        # Ответственный: руководитель, а если его нет, то исполнитель
        return self.supervisor or self.assignee