from __future__ import annotations

from pydantic import BaseModel


class CartItemOut(BaseModel):
    product_id: int
    weight: int


class CartOut(BaseModel):
    items: list[CartItemOut]

