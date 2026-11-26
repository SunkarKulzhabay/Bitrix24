import argparse
import asyncio
import getpass

from sqlalchemy import select

from backend.app.auth.security import hash_password
from backend.app.database import SessionLocal, engine
from backend.app.employees.models import Employee


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--login", required=True)
    parser.add_argument("--password", help="если не указан, будет запрошен")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Новый пароль: ")
    if len(password) < 8:
        raise SystemExit("Пароль должен быть не короче 8 символов")

    login = args.login.strip().lower()

    async with SessionLocal() as session:
        result = await session.execute(select(Employee).where(Employee.login == login))
        employee = result.scalar_one_or_none()
        if employee is None:
            raise SystemExit(f"Пользователь «{login}» не найден")

        employee.password_hash = hash_password(password)
        employee.is_active = True  # заодно включит учётную запись, если её отключили
        await session.commit()

    await engine.dispose()
    print(f"Пароль для «{login}» изменён")


if __name__ == "__main__":
    asyncio.run(main())