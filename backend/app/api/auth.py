"""Авторизация родительской панели (frontend-admin).

Намеренно простая модель: один общий пароль на обоих родителей вместо
полноценных аккаунтов — соразмерно задаче (2 пользователя, семейное
использование). "Токен" в ответе login — это и есть пароль: клиент
хранит его и присылает как `Authorization: Bearer <пароль>` на каждый
защищённый запрос. Секретности сессии это не добавляет (пароль и есть
секрет), но избавляет от хранения сессий на сервере.
"""

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    if not settings.admin_dashboard_password:
        raise HTTPException(
            status_code=500, detail="ADMIN_DASHBOARD_PASSWORD не настроен на сервере"
        )
    if payload.password != settings.admin_dashboard_password:
        raise HTTPException(status_code=401, detail="Неверный пароль")
    return LoginResponse(token=settings.admin_dashboard_password)


def require_parent_auth(authorization: str | None = Header(default=None)) -> None:
    if not settings.admin_dashboard_password:
        # Пароль не настроен (локальная разработка) — не блокируем доступ.
        return
    if authorization != f"Bearer {settings.admin_dashboard_password}":
        raise HTTPException(status_code=401, detail="Требуется авторизация родительской панели")
