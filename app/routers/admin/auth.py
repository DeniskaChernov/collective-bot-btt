from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.config import Settings
from app.schemas.admin import AdminLoginIn, AdminTokenOut
from app.schemas.response import err, ok
from app.security.jwt import create_access_token
from app.security.passwords import verify_password
from app.security.rate_limit import admin_rate_limit

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

    if not verify_password(payload.password, settings.admin_password_hash):
        return JSONResponse(
            status_code=401,
            content=err("invalid_credentials", "Invalid credentials").model_dump(),
        )

    token = create_access_token(settings, subject=payload.username)
    return ok(AdminTokenOut(access_token=token))

