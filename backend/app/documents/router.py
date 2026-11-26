from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import get_current_user
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.documents.models import ApprovalRequest, Document, DocumentTemplate
from backend.app.documents.schemas import (
    DecisionRequest,
    DocumentCreate,
    DocumentOut,
    SendRequest,
    TemplateOut,
)
from backend.app.documents.service import render_document
from backend.app.employees.models import Employee

router = APIRouter(prefix="/api/documents", tags=["documents"])


def can_view(document: Document, user: Employee) -> bool:
    return (
        user.role == "admin"
        or document.requester_id == user.id
        or any(a.approver_id == user.id for a in document.approvals)
    )


def to_out(document: Document, user: Employee) -> DocumentOut:
    out = DocumentOut.model_validate(document)
    out.stamp_text = settings.COMPANY_NAME
    out.can_send = document.requester_id == user.id and document.status in ("draft", "rejected")
    out.can_decide = document.status == "on_approval" and any(
        a.approver_id == user.id and a.status == "waiting" for a in document.approvals
    )
    return out


async def fetch_document(db: AsyncSession, document_id: int) -> Document | None:
    result = await db.execute(
        select(Document).where(Document.id == document_id).execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def load_document(db: AsyncSession, document_id: int, user: Employee) -> Document:
    document = await fetch_document(db, document_id)
    if document is None or not can_view(document, user):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Документ не найден")
    return document


# Этот маршрут должен стоять выше "/{document_id}"
@router.get("/templates", response_model=list[TemplateOut])
async def list_templates(db: AsyncSession = Depends(get_db), _: Employee = Depends(get_current_user)):
    result = await db.execute(select(DocumentTemplate).order_by(DocumentTemplate.name))
    return result.scalars().all()


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    view: Literal["mine", "approval"] = "mine",
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    if view == "mine":
        condition = Document.requester_id == user.id
    else:
        condition = Document.approvals.any(
            and_(ApprovalRequest.approver_id == user.id, ApprovalRequest.status == "waiting")
        )
    result = await db.execute(select(Document).where(condition).order_by(Document.id.desc()))
    return [to_out(document, user) for document in result.scalars().all()]


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def create_document(
    data: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    template = await db.get(DocumentTemplate, data.template_id)
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Шаблон не найден")

    content, values = render_document(template, data.values, user.full_name)

    document = Document(
        template_id=template.id,
        title=template.name,
        content=content,
        field_values=values,
        with_stamp=data.with_stamp,
        requester_id=user.id,
    )
    db.add(document)
    await db.flush()
    document.number = f"{datetime.now().year}-{document.id:04d}"
    await db.commit()

    return to_out(await fetch_document(db, document.id), user)


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    return to_out(await load_document(db, document_id, user), user)


@router.post("/{document_id}/send", response_model=DocumentOut)
async def send_for_approval(
    document_id: int,
    data: SendRequest,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    document = await load_document(db, document_id, user)
    if document.requester_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Отправить может только автор документа")
    if document.status not in ("draft", "rejected"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Документ нельзя отправить на одобрение")
    if data.approver_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Нельзя отправить документ самому себе")

    approver = await db.get(Employee, data.approver_id)
    if approver is None or not approver.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Сотрудник не найден или отключён")

    db.add(ApprovalRequest(document_id=document.id, approver_id=approver.id))
    document.status = "on_approval"
    await db.commit()

    return to_out(await fetch_document(db, document_id), user)


@router.post("/{document_id}/decision", response_model=DocumentOut)
async def decide(
    document_id: int,
    data: DecisionRequest,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    document = await load_document(db, document_id, user)
    approval = next(
        (a for a in document.approvals if a.approver_id == user.id and a.status == "waiting"), None
    )
    if document.status != "on_approval" or approval is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "У вас нет запроса на одобрение этого документа")

    comment = data.comment.strip()
    if data.decision == "rejected" and not comment:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Укажите причину отклонения")

    approval.status = data.decision
    approval.comment = comment
    approval.decided_at = datetime.now()
    document.status = data.decision
    await db.commit()

    return to_out(await fetch_document(db, document_id), user)