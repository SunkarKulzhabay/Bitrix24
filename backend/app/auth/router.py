from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import throttle
from backend.app.auth.dependencies import get_current_user
from backend.app.auth.schemas import (
    CurrentUser,
    LoginRequest,
    PasswordChangeRequest,
    TokenResponse,
)
from backend.app.auth.security import (
    DUMMY_HASH,
    create_access_token,
    hash_password,
    verify_password,
)
from backend.app.database import get_db
from backend.app.employees.models import Employee

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db)):
    login_value = data.login.strip().lower()
    throttle.check_allowed(request, login_value)

    result = await db.execute(select(Employee).where(Employee.login == login_value))
    employee = result.scalar_one_or_none()

    hash_to_check = employee.password_hash if employee else DUMMY_HASH
    password_ok = await run_in_threadpool(verify_password, data.password, hash_to_check)

    if employee is None or not password_ok or not employee.is_active:
        throttle.register_failure(request, login_value)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный логин или пароль")

    throttle.reset(request, login_value)
    return TokenResponse(access_token=create_access_token(employee.id))


@router.get("/me", response_model=CurrentUser)
async def me(user: Employee = Depends(get_current_user)):
    return user


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    current_ok = await run_in_threadpool(verify_password, data.current_password, user.password_hash)
    if not current_ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Текущий пароль указан неверно")
    if data.current_password == data.new_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Новый пароль должен отличаться от текущего")

    user.password_hash = await run_in_threadpool(hash_password, data.new_password)
    await db.commit()