from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFound, ValidationError
from app.models import Product, ProductStatus
from app.notifications import send_admin_notification

logger = logging.getLogger(__name__)


async def list_products(session: AsyncSession) -> list[Product]:
    stmt = select(Product).order_by(Product.created_at.desc())
    return list((await session.execute(stmt)).scalars().all())


async def get_product(session: AsyncSession, *, product_id: int) -> Product:
    product = (await session.execute(select(Product).where(Product.id == product_id))).scalar_one_or_none()
    if product is None:
        raise NotFound("Product not found", details={"product_id": product_id})
    return product


async def create_product(
    session: AsyncSession,
    *,
    article: str,
    name: str,
    profile: str,
    image_url: str | None,
    min_weight: int,
) -> Product:
    if min_weight <= 0:
        raise ValidationError("min_weight must be positive")

    async with session.begin():
        product = Product(
            article=article,
            name=name,
            profile=profile,
            image_url=image_url,
            min_weight=min_weight,
            total_weight=0,
            status=ProductStatus.open,
            threshold_reached_at=None,
        )
        session.add(product)
        await session.flush()
        return product


async def update_product(
    session: AsyncSession,
    *,
    product_id: int,
    article: str | None = None,
    name: str | None = None,
    profile: str | None = None,
    image_url: str | None = None,
    min_weight: int | None = None,
) -> Product:
    async with session.begin():
        product = (
            await session.execute(
                select(Product).where(Product.id == product_id).with_for_update()
            )
        ).scalar_one_or_none()
        if product is None:
            raise NotFound("Product not found", details={"product_id": product_id})

        if min_weight is not None and min_weight <= 0:
            raise ValidationError("min_weight must be positive")

        if article is not None:
            product.article = article
        if name is not None:
            product.name = name
        if profile is not None:
            product.profile = profile
        if image_url is not None:
            product.image_url = image_url
        if min_weight is not None:
            product.min_weight = min_weight
        await session.flush()
        return product


async def manual_close_product(session: AsyncSession, *, product_id: int) -> Product:
    async with session.begin():
        product = (
            await session.execute(
                select(Product).where(Product.id == product_id).with_for_update()
            )
        ).scalar_one_or_none()
        if product is None:
            raise NotFound("Product not found", details={"product_id": product_id})
        product.status = ProductStatus.closed
        logger.info("product.closed", extra={"product_id": product_id, "source": "admin"})
        await session.flush()
    await send_admin_notification(f"🚫 Партия #{product_id} закрыта администратором")
    return product


async def manual_reopen_product(session: AsyncSession, *, product_id: int) -> Product:
    async with session.begin():
        product = (
            await session.execute(
                select(Product).where(Product.id == product_id).with_for_update()
            )
        ).scalar_one_or_none()
        if product is None:
            raise NotFound("Product not found", details={"product_id": product_id})
        product.status = ProductStatus.open
        product.total_weight = 0
        product.threshold_reached_at = None
        logger.info("product.reopened", extra={"product_id": product_id, "source": "admin"})
        await session.flush()
    await send_admin_notification(f"🔄 Партия #{product_id} переоткрыта администратором")
    return product

