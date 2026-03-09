from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    phone: str | None
    language: str | None
    created_at: datetime


class UserWithStatsOut(UserOut):
    total_orders: int
    total_weight: int


class MeOut(BaseModel):
    """Профиль текущего пользователя для Mini App."""

    id: int
    first_name: str | None
    username: str | None
    language: str | None
    has_phone: bool
    phone_masked: str | None  # последние 4 цифры для отображения


class UserLanguageUpdateIn(BaseModel):
    language: str

