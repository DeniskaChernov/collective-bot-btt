from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.config import Settings
from app.schemas.admin import AdminLoginIn, AdminTokenOut
from app.schemas.response import err, ok
from app.security.jwt import create_access_token
from app.security.passwords import verify_password
from app.security.rate_limit import admin_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


def _settings(request: Request) -> Settings:
    return request.app.state.settings


@router.post("/login", dependencies=[Depends(admin_rate_limit)])
async def login(payload: AdminLoginIn, request: Request):
    settings = _settings(request)
    if payload.username != settings.admin_username:
        return JSONResponse(
            status_code=401,
            content=err("invalid_credentials", "Invalid credentials").model_dump(),
        )

    hash_value = (settings.admin_password_hash or "").strip()
    if not hash_value:
        return JSONResponse(
            status_code=503,
            content=err(
                "config_error",
                "ADMIN_PASSWORD_HASH не задан. Сгенерируй хеш: python -c \"import passlib.hash; print(passlib.hash.bcrypt.hash('admin123'))\" и вставь в Variables в Railway.",
            ).model_dump(),
        )

    try:
        if not verify_password(payload.password, hash_value):
            return JSONResponse(
                status_code=401,
                content=err("invalid_credentials", "Неверный логин или пароль").model_dump(),
            )
    except Exception as e:
        logger.exception("admin_login_verify_failed")
        return JSONResponse(
            status_code=503,
            content=err(
                "config_error",
                "ADMIN_PASSWORD_HASH задан неверно (не bcrypt). Сгенерируй заново: python -c \"import passlib.hash; print(passlib.hash.bcrypt.hash('admin123'))\" и замени значение в Railway.",
            ).model_dump(),
        )

    token = create_access_token(settings, subject=payload.username)
    return ok(AdminTokenOut(access_token=token))

