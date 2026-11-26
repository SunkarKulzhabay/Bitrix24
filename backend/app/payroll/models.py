from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base
from backend.app.employees.models import Employee
from backend.app.projects.models import Project


class SalarySetting(Base):
    __tablename__ = "salary_settings"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), primary_key=True)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)


class TimesheetEntry(Base):
    __tablename__ = "timesheet_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    work_date: Mapped[date] = mapped_column(Date)
    hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    created_by_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))

    project: Mapped[Project] = relationship(lazy="joined")


class KpiMetric(Base):
    __tablename__ = "kpi_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    target_value: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    bonus_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    mode: Mapped[str] = mapped_column(String(20), default="proportional")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class KpiResult(Base):
    __tablename__ = "kpi_results"
    __table_args__ = (UniqueConstraint("employee_id", "metric_id", "month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    metric_id: Mapped[int] = mapped_column(ForeignKey("kpi_metrics.id"))
    month: Mapped[date] = mapped_column(Date)
    actual_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    metric: Mapped[KpiMetric] = relationship(lazy="joined")


class Penalty(Base):
    __tablename__ = "penalties"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    issued_at: Mapped[date] = mapped_column(Date)
    issued_by_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    issued_by: Mapped[Employee] = relationship(foreign_keys=[issued_by_id], lazy="joined")