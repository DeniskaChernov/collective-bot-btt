from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import Order


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    product_id: int
    weight_total: int
    status: Order.OrderStatus
    fulfillment_type: Order.FulfillmentType
    delivery_address: str | None
    comment: str | None
    created_at: datetime
    product_name: str | None = None
    product_article: str | None = None
    product_image_url: str | None = None
    product_color: str | None = None
    product_thread_width: str | None = None


class AdminOrderOut(OrderOut):
    """Заказ с контактами заказчика для админки (связь, предоплата)."""

    user_phone: str | None = None
    user_telegram_id: int | None = None
    user_username: str | None = None
    user_first_name: str | None = None
    telegram_link: str | None = None


class OrderCreateIn(BaseModel):
    fulfillment_type: Order.FulfillmentType
    delivery_address: str | None = Field(None, max_length=500)
    comment: str | None = Field(None, max_length=1000)


class OrderStatusUpdateIn(BaseModel):
    status: Order.OrderStatus

