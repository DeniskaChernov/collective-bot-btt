from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product, ProductStatus, User
from app.services.cart import STEP_KG, add_to_cart_5kg, get_cart, remove_from_cart_5kg
from app.services.orders import create_order_from_cart


@pytest.mark.asyncio
async def test_cart_add_and_remove(session: AsyncSession) -> None:
    user = User(telegram_id=123)
    product = Product(
        article="A1",
        name="Test",
        profile="P",
        min_weight=100,
        total_weight=0,
        status=ProductStatus.open,
    )
    session.add_all([user, product])
    await session.commit()

    item = await add_to_cart_5kg(session, user_id=user.id, product_id=product.id)
    assert item.weight == STEP_KG

    item = await add_to_cart_5kg(session, user_id=user.id, product_id=product.id)
    assert item.weight == 2 * STEP_KG

    item_after_remove = await remove_from_cart_5kg(session, user_id=user.id, product_id=product.id)
    assert item_after_remove is not None
    assert item_after_remove.weight == STEP_KG

    item_after_remove2 = await remove_from_cart_5kg(session, user_id=user.id, product_id=product.id)
    assert item_after_remove2 is None

    cart = await get_cart(session, user_id=user.id)
    assert cart == []


@pytest.mark.asyncio
async def test_order_creation_reaches_threshold_and_schedules(
    session: AsyncSession, scheduler: AsyncIOScheduler
) -> None:
    user = User(telegram_id=1, phone="+10000000000")
    product = Product(
        article="B1",
        name="Bulk",
        profile="P",
        min_weight=10,
        total_weight=0,
        status=ProductStatus.open,
    )
    session.add_all([user, product])
    await session.commit()

    # cart: 10 kg
    await add_to_cart_5kg(session, user_id=user.id, product_id=product.id)
    await add_to_cart_5kg(session, user_id=user.id, product_id=product.id)

    order = await create_order_from_cart(
        session,
        scheduler=scheduler,
        user_id=user.id,
        product_id=product.id,
    )
    assert order.weight_total == 10

    refreshed = await session.get(Product, product.id)
    assert refreshed is not None
    assert refreshed.total_weight == 10
    assert refreshed.status == ProductStatus.waiting_24h
    assert refreshed.threshold_reached_at is not None

    job = scheduler.get_job(f"close_product:{product.id}")
    assert job is not None


@pytest.mark.asyncio
async def test_cannot_add_order_after_batch_closed(session: AsyncSession, scheduler: AsyncIOScheduler) -> None:
    now = datetime.now(timezone.utc)
    user = User(telegram_id=2, phone="+10000000001")
    product = Product(
        article="C1",
        name="Closed",
        profile="P",
        min_weight=10,
        total_weight=10,
        status=ProductStatus.waiting_24h,
        threshold_reached_at=now - timedelta(hours=25),
    )
    session.add_all([user, product])
    await session.commit()

    await add_to_cart_5kg(session, user_id=user.id, product_id=product.id)

    with pytest.raises(Exception):
        await create_order_from_cart(
            session,
            scheduler=scheduler,
            user_id=user.id,
            product_id=product.id,
        )

