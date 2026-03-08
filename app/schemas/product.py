from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models import ProductStatus


def _normalize_image_url(v: str | None) -> str | None:
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    s = v.strip()
    # Разрешаем свои загрузки (/uploads/...) и внешние ссылки (http/https)
    if s.startswith(("/", "http://", "https://")):
        return s
    return None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    article: str
    name: str
    profile: str
    image_url: str | None
    thread_width: str | None
    color: str | None
    min_weight: int
    max_weight_per_order: int
    total_weight: int
    status: ProductStatus
    threshold_reached_at: datetime | None
    collection_until: datetime | None

    @field_validator("image_url", mode="before")
    @classmethod
    def empty_image_to_none(cls, v: str | None) -> str | None:
        return _normalize_image_url(v)


class ProductCreateIn(BaseModel):
    article: str
    name: str
    profile: str = ""
    image_url: str | None = None
    thread_width: str | None = None
    color: str | None = None
    min_weight: int = 100
    max_weight_per_order: int = 25


class ProductUpdateIn(BaseModel):
    article: str | None = None
    name: str | None = None
    profile: str | None = None
    image_url: str | None = None
    thread_width: str | None = None
    color: str | None = None
    min_weight: int | None = None
    max_weight_per_order: int | None = None

