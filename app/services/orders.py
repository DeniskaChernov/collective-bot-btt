from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFound, ValidationError
from app.models import Order, Product, ProductStatus, User
from app.notifications import send_admin_notification, send_user_notification
from app.services.cart import clear_cart_item, get_cart_item_for_update
from app.services.scheduler import schedule_close_product
from app.services.users import get_user

logger = logging.getLogger(__name__)


async def create_order_from_cart(
    session: AsyncSession,
    *,
    scheduler: AsyncIOScheduler | None,
    user_id: int,
    product_id: int,
    fulfillment_type: Order.FulfillmentType,
    delivery_address: str | None = None,
    comment: str | None = None,
) -> Order:
    schedule_at: datetime | None = None
    should_schedule_product_id: int | None = None

    async with session.begin():
        user = await get_user(session, user_id=user_id)
        if not user.phone:
            raise ValidationError("User phone is required")

        cart_item = await get_cart_item_for_update(session, user_id=user_id, product_id=product_id)
        if cart_item.weight <= 0:
            raise ValidationError("Cart item weight must be positive")

        product = (
            await session.execute(
                select(Product).where(Product.id == product_id).with_for_update()
            )
        ).scalar_one_or_none()
        if product is None:
            raise NotFound("Product not found", details={"product_id": product_id})
        if product.status == ProductStatus.closed:
            raise ValidationError("Product batch is closed")
        if (
            product.status == ProductStatus.waiting_24h
            and product.threshold_reached_at is not None
            and product.threshold_reached_at + timedelta(hours=24) <= datetime.now(timezone.utc)
        ):
            product.status = ProductStatus.closed
            raise ValidationError("Product batch is closed")

        if fulfillment_type == Order.FulfillmentType.delivery and not delivery_address:
            raise ValidationError("Delivery address is required for delivery")

        order = Order(
            user_id=user_id,
            product_id=product_id,
            weight_total=cart_item.weight,
            fulfillment_type=fulfillment_type,
            delivery_address=delivery_address,
            comment=comment,
        )
        session.add(order)

        product.total_weight += cart_item.weight

        threshold_reached_now = False
        if product.status == ProductStatus.open and product.total_weight >= product.min_weight:
            product.status = ProductStatus.waiting_24h
            product.threshold_reached_at = datetime.now(timezone.utc)
            schedule_at = product.threshold_reached_at + timedelta(hours=24)
            should_schedule_product_id = product.id
            threshold_reached_now = True
            logger.info(
                "product.threshold_reached",
                extra={"product_id": product.id, "threshold_reached_at": product.threshold_reached_at.isoformat()},
            )

        await clear_cart_item(session, user_id=user_id, product_id=product_id)
        await session.flush()

    logger.info("order.created", extra={"order_id": order.id, "user_id": user_id, "product_id": product_id})
    await send_admin_notification(
        f"🧾 Новый заказ #{order.id}: пользователь {user_id}, товар {product_id}, вес {order.weight_total} кг"
    )

    # Уведомление пользователя о заказе
    if user.telegram_id:
        await send_user_notification(
            user.telegram_id,
            f"✅ Заказ создан: товар #{product_id}, {order.weight_total} кг.\n"
            "Мы уведомим вас о запуске и закрытии партии.",
        )

    # Если только что достигли порога 100 кг — уведомляем всех участников партии
    if threshold_reached_now:
        stmt = select(User.telegram_id).join(Order, Order.user_id == User.id).where(
            Order.product_id == product_id
        )
        rows = (await session.execute(stmt)).all()
        notified_ids: set[int] = set()
        for (tg_id,) in rows:
            if tg_id and tg_id not in notified_ids:
                notified_ids.add(tg_id)
                await send_user_notification(
                    int(tg_id),
                    "🎉 Партия достигла 100 кг!\nЗапущен добор 24 часа. "
                    "Вы можете увеличить заказ до закрытия партии.",
                )

    if scheduler is not None and should_schedule_product_id is not None and schedule_at is not None:
        schedule_close_product(scheduler, product_id=int(should_schedule_product_id), run_at=schedule_at)
        logger.info(
            "scheduler.job_scheduled",
            extra={"job_id": f"close_product:{should_schedule_product_id}", "product_id": should_schedule_product_id},
        )

    return order

