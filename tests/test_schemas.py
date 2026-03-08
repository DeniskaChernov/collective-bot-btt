"""Тесты валидации схем заказа."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.order import OrderCreateIn


def test_order_create_in_delivery_address_max_length() -> None:
    OrderCreateIn(fulfillment_type="delivery", delivery_address="a" * 500)
    with pytest.raises(ValidationError):
        OrderCreateIn(fulfillment_type="delivery", delivery_address="a" * 501)


def test_order_create_in_comment_max_length() -> None:
    OrderCreateIn(fulfillment_type="pickup", comment="a" * 1000)
    with pytest.raises(ValidationError):
        OrderCreateIn(fulfillment_type="pickup", comment="a" * 1001)
