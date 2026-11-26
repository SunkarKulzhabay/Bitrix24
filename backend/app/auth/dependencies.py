from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.security import decode_access_token
from backend.app.database import get_db
from backend.app.employees.models import Employee

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> Employee:
    error = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Требуется вход в систему",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise error

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise error

    try:
        employee_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise error

    # Сотрудника берём из базы при каждом запросе: если его отключили
    # или сменили роль, это действует сразу, а не после окончания токена.
    employee = await db.get(Employee, employee_id)
    if employee is None or not employee.is_active:
        raise error
    return employee


def require_roles(*roles: str):
    async def checker(user: Employee = Depends(get_current_user)) -> Employee:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
        return user

    return checker
