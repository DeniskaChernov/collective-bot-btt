"""Тесты сервиса users: normalize_phone, set_user_phone."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.services.users import get_user, normalize_phone, set_user_phone


def test_normalize_phone() -> None:
    assert normalize_phone("+998901234567") == "+998901234567"
    assert normalize_phone("998 90 123 45 67") == "998901234567"
    assert normalize_phone("  +7 999 123-45-67  ") == "+79991234567"
    assert normalize_phone("") == ""
    assert normalize_phone("abc") == ""
    assert len(normalize_phone("+" + "9" * 40)) <= 32


@pytest.mark.asyncio
async def test_set_user_phone_rejects_empty(session: AsyncSession) -> None:
    user = User(telegram_id=1)
    session.add(user)
    await session.commit()
    from app.errors import ValidationError
    with pytest.raises(ValidationError, match="Некорректный"):
        await set_user_phone(session, user_id=user.id, phone="   ")
    with pytest.raises(ValidationError, match="Некорректный"):
        await set_user_phone(session, user_id=user.id, phone="abc")


@pytest.mark.asyncio
async def test_set_user_phone_normalizes(session: AsyncSession) -> None:
    user = User(telegram_id=2)
    session.add(user)
    await session.commit()
    await set_user_phone(session, user_id=user.id, phone="+998 90 123-45-67")
    assert user.phone == "+998901234567"
