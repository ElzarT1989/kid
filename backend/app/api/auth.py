"""Авторизация родительской панели (frontend-admin).

Намеренно простая модель: один общий пароль на обоих родителей вместо
полноценных аккаунтов — соразмерно задаче (2 пользователя, семейное
использование).

Токен в ответе login — это base64 от пароля, а не сам пароль в открытом
виде. Это не про секретность (пароль и так секрет), а про то, что HTTP-
заголовки (Authorization: Bearer <токен>) обязаны быть ASCII/Latin-1 —
браузерный fetch() бросает TypeError при попытке собрать заголовок с
кириллицей или любым другим не-ASCII символом, и запрос даже не уходит
в сеть. Пароль при этом может быть каким угодно (в т.ч. с кириллицей —
он передаётся в теле JSON-запроса, где юникод не ограничен), а в
заголовок всегда попадает безопасная base64-строка.
"""

import base64
import binascii

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str


def _encode_token(password: str) -> str:
    return base64.b64encode(password.encode("utf-8")).decode("ascii")


def _decode_token(token: str) -> str | None:
    try:
        return base64.b64decode(token.encode("ascii"), validate=True).decode("utf-8")
    except (binascii.Error, ValueError):
        return None


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    if not settings.admin_dashboard_password:
        raise HTTPException(
            status_code=500, detail="ADMIN_DASHBOARD_PASSWORD не настроен на сервере"
        )
    if payload.password != settings.admin_dashboard_password:
        raise HTTPException(status_code=401, detail="Неверный пароль")
    return LoginResponse(token=_encode_token(settings.admin_dashboard_password))


def require_parent_auth(authorization: str | None = Header(default=None)) -> None:
    if not settings.admin_dashboard_password:
        # Пароль не настроен (локальная разработка) — не блокируем доступ.
        return
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Требуется авторизация родительской панели")

    token = authorization.removeprefix("Bearer ")
    if _decode_token(token) != settings.admin_dashboard_password:
        raise HTTPException(status_code=401, detail="Требуется авторизация родительской панели")
