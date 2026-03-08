from __future__ import annotations

from fastapi import Depends, Header, Request

from app.config import Settings
from app.errors import Forbidden
from app.security.jwt import decode_access_token


def _get_settings(request: Request) -> Settings:
    return request.app.state.settings


async def require_admin(
    request: Request,
    authorization: str | None = Header(default=None),
) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Forbidden("Missing authorization header")
    token = authorization.split(" ", 1)[1].strip()
    settings = _get_settings(request)
    try:
        claims = decode_access_token(settings, token)
    except ValueError:
        raise Forbidden("Invalid token")
    return claims.sub

