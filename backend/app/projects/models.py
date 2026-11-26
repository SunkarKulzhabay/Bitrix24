from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base
from backend.app.employees.models import Employee


class Partner(Base):
    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    contact_person: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"))
    services: Mapped[str] = mapped_column(Text, default="")
    deal_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    stage: Mapped[str] = mapped_column(String(30), default="new")
    refusal_reason: Mapped[str] = mapped_column(Text, default="")
    curator_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    partner: Mapped[Partner] = relationship(lazy="joined")
    curator: Mapped[Employee] = relationship(lazy="joined")
    members: Mapped[list["ProjectMember"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="ProjectMember.id"
    )
    history: Mapped[list["StageChange"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="StageChange.id.desc()"
    )


class ProjectMember(Base):
    __tablename__ = "project_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    role: Mapped[str] = mapped_column(String(100))
    reports_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("project_members.id", ondelete="SET NULL"), nullable=True
    )

    employee: Mapped[Employee] = relationship(lazy="joined")


class StageChange(Base):
    __tablename__ = "stage_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    from_stage: Mapped[str] = mapped_column(String(30), default="")
    to_stage: Mapped[str] = mapped_column(String(30))
    changed_by_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    comment: Mapped[str] = mapped_column(Text, default="")

    changed_by: Mapped[Employee] = relationship(lazy="joined")