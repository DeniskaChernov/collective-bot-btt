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


class OrderCreateIn(BaseModel):
    fulfillment_type: Order.FulfillmentType
    delivery_address: str | None = Field(None, max_length=500)
    comment: str | None = Field(None, max_length=1000)


class OrderStatusUpdateIn(BaseModel):
    status: Order.OrderStatus

