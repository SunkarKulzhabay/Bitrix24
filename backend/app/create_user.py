"""Создание пользователя из командной строки.

Регистрации в системе нет, поэтому первого пользователя (администратора)
создаём этим скриптом:

    python -m backend.app.create_user --login admin --name "Иван Иванов" --role admin
"""
import argparse
import asyncio
import getpass

from sqlalchemy import select

from backend.app.auth.security import hash_password
from backend.app.database import Base, SessionLocal, engine
from backend.app.employees.models import ROLES, Employee


async def main() -> None:
    parser = argparse.ArgumentParser(description="Создать пользователя CRM")
    parser.add_argument("--login", required=True)
    parser.add_argument("--name", required=True, help="ФИО")
    parser.add_argument("--role", default="employee", choices=ROLES)
    parser.add_argument("--password", help="если не указан, будет запрошен")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Пароль: ")
    if len(password) < 8:
        raise SystemExit("Пароль должен быть не короче 8 символов")

    login = args.login.strip().lower()

    async with SessionLocal() as session:
        exists = await session.execute(select(Employee).where(Employee.login == login))
        if exists.scalar_one_or_none():
            raise SystemExit(f"Логин «{login}» уже занят")

        session.add(
            Employee(
                full_name=args.name.strip(),
                login=login,
                password_hash=hash_password(password),
                role=args.role,
            )
        )
        await session.commit()

    await engine.dispose()
    print(f"Пользователь «{login}» создан с ролью «{args.role}»")


if __name__ == "__main__":
    asyncio.run(main())
