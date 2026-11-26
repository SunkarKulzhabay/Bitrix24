"""Резервная копия данных без pg_dump (его блокирует политика Windows).

Копия:          python -m backend.app.backup
Восстановление: python -m backend.app.backup --restore backups\\crm_db_ДАТА.json
                (в пустую базу, где уже выполнено: python -m alembic upgrade head)
"""
import argparse
import asyncio
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import Date, DateTime, Numeric, func, insert, select, text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.app.config import settings
from backend.app.database import Base

# Модели всех модулей, чтобы в копию попали все таблицы
from backend.app.documents import models as _documents  # noqa: F401
from backend.app.employees import models as _employees  # noqa: F401
from backend.app.events import models as _events  # noqa: F401
from backend.app.payroll import models as _payroll  # noqa: F401
from backend.app.projects import models as _projects  # noqa: F401
from backend.app.tasks import models as _tasks  # noqa: F401

BACKUP_DIR = Path(__file__).resolve().parents[2] / "backups"
KEEP_LAST = 14  # сколько последних копий хранить


def encode(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def decode(column, value):
    if value is None:
        return None
    column_type = column.type
    if isinstance(column_type, DateTime):
        return datetime.fromisoformat(value)
    if isinstance(column_type, Date):
        return date.fromisoformat(value)
    if isinstance(column_type, Numeric):
        return Decimal(value)
    return value


def order_self_referencing(table, rows):
    """Строки, которые ссылаются на строки той же таблицы (руководитель и т.п.), идут после них."""
    refs = [fk.parent.name for fk in table.foreign_keys if fk.column.table is table]
    if not refs:
        return rows

    pk = list(table.primary_key.columns)[0].name
    pending = list(rows)
    done: set = set()
    ordered = []
    while pending:
        rest = []
        for row in pending:
            if all(row[ref] is None or row[ref] in done for ref in refs):
                ordered.append(row)
                done.add(row[pk])
            else:
                rest.append(row)
        if len(rest) == len(pending):
            raise RuntimeError(f"Не удаётся упорядочить строки таблицы {table.name}")
        pending = rest
    return ordered


async def make_backup() -> int:
    # REPEATABLE READ: все таблицы читаются как один согласованный снимок
    engine = create_async_engine(settings.DATABASE_URL, isolation_level="REPEATABLE READ")
    tables: dict[str, list] = {}
    try:
        async with engine.connect() as connection:
            for table in Base.metadata.sorted_tables:
                rows = (await connection.execute(select(table))).mappings().all()
                tables[table.name] = [
                    {key: encode(value) for key, value in row.items()} for row in rows
                ]
    except Exception as error:
        print("Не удалось прочитать данные из базы:", error)
        return 1
    finally:
        await engine.dispose()

    database = urlparse(settings.DATABASE_URL).path.lstrip("/")
    BACKUP_DIR.mkdir(exist_ok=True)
    target = BACKUP_DIR / f"{database}_{datetime.now():%Y-%m-%d_%H-%M-%S}.json"
    payload = {"created_at": datetime.now().isoformat(timespec="seconds"), "tables": tables}
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    for old in sorted(BACKUP_DIR.glob(f"{database}_*.json"))[:-KEEP_LAST]:
        old.unlink()

    total = sum(len(rows) for rows in tables.values())
    print(f"Копия сохранена: {target} (строк: {total})")
    return 0


async def restore(path: Path, url: str) -> int:
    if not path.exists():
        print("Файл копии не найден:", path)
        return 1

    data = json.loads(path.read_text(encoding="utf-8"))["tables"]
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            for table in Base.metadata.sorted_tables:
                count = (await connection.execute(select(func.count()).select_from(table))).scalar()
                if count:
                    print(f"Таблица {table.name} не пустая. Восстанавливать можно только в пустую базу.")
                    return 1

            for table in Base.metadata.sorted_tables:
                rows = data.get(table.name, [])
                if not rows:
                    continue
                prepared = [
                    {column.name: decode(column, row.get(column.name)) for column in table.columns}
                    for row in order_self_referencing(table, rows)
                ]
                await connection.execute(insert(table), prepared)

            # Счётчики id продолжаются после последней восстановленной строки
            for table in Base.metadata.sorted_tables:
                if "id" in table.columns:
                    name = table.name
                    await connection.execute(
                        text(
                            f"SELECT setval(pg_get_serial_sequence('{name}', 'id'), "
                            f"COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM {name}"
                        )
                    )
    except Exception as error:
        print("Не удалось восстановить, изменения отменены:", error)
        return 1
    finally:
        await engine.dispose()

    print("Данные восстановлены")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Резервная копия данных CRM")
    parser.add_argument("--restore", metavar="ФАЙЛ", help="восстановить данные из файла копии")
    parser.add_argument("--url", default=settings.DATABASE_URL, help="в какую базу восстанавливать")
    args = parser.parse_args()

    if args.restore:
        return asyncio.run(restore(Path(args.restore), args.url))
    return asyncio.run(make_backup())


if __name__ == "__main__":
    sys.exit(main())