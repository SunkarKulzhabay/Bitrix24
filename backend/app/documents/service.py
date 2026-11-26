import re
from datetime import datetime

from fastapi import HTTPException, status

from backend.app.config import settings
from backend.app.documents.models import DocumentTemplate

PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def bad_request(message: str) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, message)


def render_document(template: DocumentTemplate, raw_values: dict[str, str], employee_name: str):
    """Возвращает (готовый текст, принятые значения полей)."""
    values: dict[str, str] = {}

    for field in template.fields:
        key = field["key"]
        label = field["label"]
        value = (raw_values.get(key) or "").strip()

        if not value:
            raise bad_request(f"Заполните поле «{label}»")
        if len(value) > 3000:
            raise bad_request(f"Слишком длинное значение в поле «{label}»")

        if field["type"] == "date":
            try:
                value = datetime.strptime(value, "%Y-%m-%d").strftime("%d.%m.%Y")
            except ValueError:
                raise bad_request(f"Неверная дата в поле «{label}»")
        elif field["type"] == "number":
            try:
                value = str(int(value))
            except ValueError:
                raise bad_request(f"В поле «{label}» нужно целое число")

        values[key] = value

    values["date"] = datetime.now().strftime("%d.%m.%Y")
    values["employee"] = employee_name
    values["company"] = settings.COMPANY_NAME

    # Один проход: если пользователь введёт в поле {{что-то}}, оно не подставится повторно
    text = PLACEHOLDER.sub(lambda match: values.get(match.group(1), ""), template.body)
    return text, values