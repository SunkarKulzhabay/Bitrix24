from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.documents.models import DocumentTemplate

# В тексте шаблона можно использовать {{поле}}.
# Всегда доступны: {{date}} (сегодня), {{employee}} (кто создаёт), {{company}} (название компании).
DEFAULT_TEMPLATES = [
    {
        "name": "Заявление на ежегодный отпуск",
        "fields": [
            {"key": "start_date", "label": "Дата начала отпуска", "type": "date"},
            {"key": "days", "label": "Количество календарных дней", "type": "number"},
        ],
        "body": (
            "Директору\n"
            "{{company}}\n\n"
            "от {{employee}}\n\n\n"
            "ЗАЯВЛЕНИЕ\n\n"
            "Прошу предоставить мне ежегодный оплачиваемый трудовой отпуск "
            "с {{start_date}} продолжительностью {{days}} календарных дней.\n\n\n"
            "Дата: {{date}}\n"
            "Подпись: ____________ / {{employee}}"
        ),
    },
    {
        "name": "Справка с места работы",
        "fields": [
            {"key": "purpose", "label": "Куда предоставляется справка", "type": "text"},
        ],
        "body": (
            "СПРАВКА\n\n"
            "Дана {{employee}} в том, что он(а) работает в {{company}}.\n\n"
            "Справка выдана для предоставления: {{purpose}}.\n\n\n"
            "Дата: {{date}}\n"
            "Руководитель: ____________"
        ),
    },
    {
        "name": "Служебная записка",
        "fields": [
            {"key": "to", "label": "Кому", "type": "text"},
            {"key": "subject", "label": "Тема", "type": "text"},
            {"key": "text", "label": "Текст записки", "type": "textarea"},
        ],
        "body": (
            "СЛУЖЕБНАЯ ЗАПИСКА\n\n"
            "Кому: {{to}}\n"
            "От: {{employee}}\n"
            "Тема: {{subject}}\n\n"
            "{{text}}\n\n\n"
            "Дата: {{date}}\n"
            "Подпись: ____________ / {{employee}}"
        ),
    },
]


async def seed_templates(session: AsyncSession) -> None:
    count = await session.scalar(select(func.count()).select_from(DocumentTemplate))
    if count:
        return
    session.add_all(DocumentTemplate(**template) for template in DEFAULT_TEMPLATES)
    await session.commit()