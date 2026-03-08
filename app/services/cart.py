from __future__ import annotations

import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFound, ValidationError
from app.models import CartItem, Product

logger = logging.getLogger(__name__)

STEP_KG = 5


async def add_to_cart_5kg(session: AsyncSession, *, user_id: int, product_id: int) -> CartItem:
    async with session.begin():
        product = (await session.execute(select(Product).where(Product.id == product_id))).scalar_one_or_none()
        if product is None:
            raise NotFound("Product not found", details={"product_id": product_id})

        item = (
            await session.execute(
                select(CartItem)
                .where(CartItem.user_id == user_id, CartItem.product_id == product_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if item is None:
            item = CartItem(user_id=user_id, product_id=product_id, weight=0)
            session.add(item)
            await session.flush()

        item.weight += STEP_KG
        await session.flush()
        logger.info("cart.add_5", extra={"user_id": user_id, "product_id": product_id, "weight": item.weight})
        return item


async def remove_from_cart_5kg(session: AsyncSession, *, user_id: int, product_id: int) -> CartItem | None:
    async with session.begin():
        item = (
            await session.execute(
                select(CartItem)
                .where(CartItem.user_id == user_id, CartItem.product_id == product_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if item is None:
            return None

        if item.weight < STEP_KG:
            raise ValidationError("Cannot decrease below zero")

        item.weight -= STEP_KG
        if item.weight == 0:
            await session.delete(item)
            logger.info("cart.remove_5", extra={"user_id": user_id, "product_id": product_id, "weight": 0})
            return None

        await session.flush()
        logger.info("cart.remove_5", extra={"user_id": user_id, "product_id": product_id, "weight": item.weight})
        return item


async def get_cart(session: AsyncSession, *, user_id: int) -> list[CartItem]:
    stmt = select(CartItem).where(CartItem.user_id == user_id).order_by(CartItem.product_id.asc())
    return list((await session.execute(stmt)).scalars().all())


async def get_cart_item_for_update(
    session: AsyncSession, *, user_id: int, product_id: int
) -> CartItem:
    item = (
        await session.execute(
            select(CartItem)
            .where(CartItem.user_id == user_id, CartItem.product_id == product_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if item is None:
        raise ValidationError("Cart is empty for this product")
    return item


async def clear_cart_item(session: AsyncSession, *, user_id: int, product_id: int) -> None:
    await session.execute(
        delete(CartItem).where(CartItem.user_id == user_id, CartItem.product_id == product_id)
    )

