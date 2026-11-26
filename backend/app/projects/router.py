from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import get_current_user, require_roles
from backend.app.database import get_db
from backend.app.employees.models import Employee
from backend.app.projects.models import Partner, Project, ProjectMember, StageChange
from backend.app.projects.schemas import MemberCreate, ProjectCreate, ProjectOut, StageRequest

router = APIRouter(prefix="/api/projects", tags=["projects"])

creators = require_roles("admin", "manager")


def can_manage(project: Project, user: Employee) -> bool:
    return user.role == "admin" or project.curator_id == user.id


def can_view(project: Project, user: Employee) -> bool:
    return can_manage(project, user) or any(m.employee_id == user.id for m in project.members)


def to_out(project: Project, user: Employee) -> ProjectOut:
    out = ProjectOut.model_validate(project)
    out.can_manage = can_manage(project, user)
    return out


async def fetch_project(db: AsyncSession, project_id: int) -> Project | None:
    result = await db.execute(
        select(Project).where(Project.id == project_id).execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def load_project(
    db: AsyncSession, project_id: int, user: Employee, manage: bool = False
) -> Project:
    project = await fetch_project(db, project_id)
    if project is None or not can_view(project, user):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Проект не найден")
    if manage and not can_manage(project, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Менять проект может куратор или администратор")
    return project


async def get_active_employee(db: AsyncSession, employee_id: int) -> Employee:
    employee = await db.get(Employee, employee_id)
    if employee is None or not employee.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Сотрудник не найден или отключён")
    return employee


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    db: AsyncSession = Depends(get_db), user: Employee = Depends(get_current_user)
):
    query = select(Project).order_by(Project.id.desc())
    if user.role != "admin":
        query = query.where(
            or_(
                Project.curator_id == user.id,
                Project.members.any(ProjectMember.employee_id == user.id),
            )
        )
    result = await db.execute(query)
    return [to_out(project, user) for project in result.scalars().all()]


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(creators),
):
    curator_id = data.curator_id or user.id
    await get_active_employee(db, curator_id)

    partner_name = data.partner_name.strip()
    result = await db.execute(
        select(Partner).where(func.lower(Partner.company_name) == partner_name.lower())
    )
    partner = result.scalar_one_or_none()
    if partner is None:
        partner = Partner(
            company_name=partner_name,
            contact_person=data.contact_person.strip(),
            phone=data.phone.strip(),
        )
        db.add(partner)
        await db.flush()

    project = Project(
        name=data.name.strip(),
        partner_id=partner.id,
        services=data.services.strip(),
        deal_amount=data.deal_amount,
        curator_id=curator_id,
    )
    db.add(project)
    await db.flush()

    db.add(StageChange(project_id=project.id, from_stage="", to_stage="new", changed_by_id=user.id))
    # Если создатель не куратор и не админ, оставляем ему доступ к проекту
    if user.id != curator_id and user.role != "admin":
        db.add(ProjectMember(project_id=project.id, employee_id=user.id, role="Создатель проекта"))
    await db.commit()

    return to_out(await fetch_project(db, project.id), user)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    return to_out(await load_project(db, project_id, user), user)


@router.post("/{project_id}/stage", response_model=ProjectOut)
async def change_stage(
    project_id: int,
    data: StageRequest,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    project = await load_project(db, project_id, user, manage=True)

    if data.stage == project.stage:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Проект уже на этой стадии")
    reason = data.reason.strip()
    if data.stage == "refused" and not reason:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Укажите причину отказа")

    db.add(
        StageChange(
            project_id=project.id,
            from_stage=project.stage,
            to_stage=data.stage,
            changed_by_id=user.id,
            comment=reason,
        )
    )
    project.stage = data.stage
    project.refusal_reason = reason if data.stage == "refused" else ""
    await db.commit()

    return to_out(await fetch_project(db, project_id), user)


@router.post("/{project_id}/members", response_model=ProjectOut)
async def add_member(
    project_id: int,
    data: MemberCreate,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    project = await load_project(db, project_id, user, manage=True)
    await get_active_employee(db, data.employee_id)

    if any(m.employee_id == data.employee_id for m in project.members):
        raise HTTPException(status.HTTP_409_CONFLICT, "Этот сотрудник уже участвует в проекте")
    if data.reports_to_id is not None and not any(m.id == data.reports_to_id for m in project.members):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Руководитель должен быть участником проекта")

    db.add(
        ProjectMember(
            project_id=project.id,
            employee_id=data.employee_id,
            role=data.role.strip(),
            reports_to_id=data.reports_to_id,
        )
    )
    await db.commit()

    return to_out(await fetch_project(db, project_id), user)


@router.delete("/{project_id}/members/{member_id}", response_model=ProjectOut)
async def remove_member(
    project_id: int,
    member_id: int,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    project = await load_project(db, project_id, user, manage=True)

    member = next((m for m in project.members if m.id == member_id), None)
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Участник не найден")

    await db.delete(member)
    await db.commit()

    return to_out(await fetch_project(db, project_id), user)