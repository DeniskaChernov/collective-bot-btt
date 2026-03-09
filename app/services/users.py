from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFound, ValidationError
from app.i18n import normalize_lang
from app.models import User


def normalize_phone(phone: str) -> str:
    """Оставляет только цифры и ведущий +, обрезает до 32 символов."""
    if not phone or not isinstance(phone, str):
        return ""
    s = re.sub(r"[^\d+]", "", phone.strip())
    if s.startswith("+"):
        return ("+" + re.sub(r"\D", "", s[1:]))[:32]
    return s[:32]


async def get_or_create_user_by_telegram_id(
    session: AsyncSession, *, telegram_id: int, username: str | None = None, first_name: str | None = None, last_name: str | None = None
) -> User:
    user = (
        await session.execute(select(User).where(User.telegram_id == telegram_id))
    ).scalar_one_or_none()
    if user is not None:
        return user

    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
    )
    session.add(user)
    await session.flush()
    return user


async def get_user(session: AsyncSession, *, user_id: int) -> User:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise NotFound("User not found", details={"user_id": user_id})
    return user


async def set_user_phone(session: AsyncSession, *, user_id: int, phone: str) -> User:
    normalized = normalize_phone(phone)
    if not normalized:
        raise ValidationError("Некорректный номер телефона")
    user = await get_user(session, user_id=user_id)
    user.phone = normalized[:32]
    await session.flush()
    return user


async def set_user_language(session: AsyncSession, *, user_id: int, language: str) -> User:
    user = await get_user(session, user_id=user_id)
    user.language = normalize_lang(language)
    await session.flush()
    return user


async def sync_user_language_if_missing(session: AsyncSession, *, user_id: int, language: str | None) -> User:
    user = await get_user(session, user_id=user_id)
    if not user.language and language:
        user.language = normalize_lang(language)
        await session.flush()
    return user


async def require_user_phone(session: AsyncSession, *, user_id: int) -> str:
    user = await get_user(session, user_id=user_id)
    if not user.phone:
        raise ValidationError("User phone is required")
    return user.phone

