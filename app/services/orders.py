from __future__ import annotations

import html
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFound, ValidationError
from app.i18n import normalize_lang, t
from app.models import Order, Product, ProductStatus, User
from app.notifications import (
    send_admin_forum_topic,
    send_admin_dm,
    send_admin_notification,
    send_user_notification,
    send_user_notifications_batch,
)
from app.services.cart import clear_cart_item, get_cart_item_for_update
from app.services.scheduler import schedule_close_product, cancel_collection_end_product
from app.services.users import get_user

logger = logging.getLogger(__name__)

PRICE_TIERS = [
    (0, 100, 36000),
    (100, 300, 34000),
    (300, 500, 31720),
]


def price_per_kg(total_weight: int) -> int:
    w = int(total_weight or 0)
    for start, end, price in PRICE_TIERS:
        if w >= start and w < end:
            return price
    return PRICE_TIERS[-1][2]


def format_sum(amount: int) -> str:
    try:
        return f"{int(amount):,}".replace(",", " ")
    except Exception:
        return str(amount)


def fulfillment_label_bilingual(value: Order.FulfillmentType) -> str:
    # RU / UZ
    if value == Order.FulfillmentType.pickup:
        return "Самовывоз / Olib ketish"
    if value == Order.FulfillmentType.delivery:
        return "Доставка / Yetkazib berish"
    if value == Order.FulfillmentType.uzum_market:
        return "Uzum Market / Uzum Market"
    return f"{value.value}"


def tier_label_ru(total_weight: int) -> str:
    w = int(total_weight or 0)
    if w < 100:
        return "до 100 кг"
    if w < 300:
        return "100–300 кг"
    return "300–500 кг"


def next_tier_remaining(total_weight: int) -> int:
    w = int(total_weight or 0)
    if w < 100:
        return 100 - w
    if w < 300:
        return 300 - w
    if w < 500:
        return 500 - w
    return 0


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
    should_notify_threshold_for_user = False

    async with session.begin():
        user = await get_user(session, user_id=user_id)
        if not user.phone:
            raise ValidationError("user_phone_required")

        cart_item = await get_cart_item_for_update(session, user_id=user_id, product_id=product_id)
        if cart_item.weight < 5:
            raise ValidationError("minimum_order_5kg")

        product = (
            await session.execute(
                select(Product).where(Product.id == product_id).with_for_update()
            )
        ).scalar_one_or_none()
        if product is None:
            raise NotFound("Product not found", details={"product_id": product_id})
        if product.status in (ProductStatus.closed, ProductStatus.cancelled):
            raise ValidationError("product_batch_closed")
        if cart_item.weight > int(product.max_weight_per_order or 25):
            raise ValidationError("maximum_order_exceeded")
        if (
            product.status == ProductStatus.waiting_24h
            and product.threshold_reached_at is not None
            and product.threshold_reached_at + timedelta(hours=24) <= datetime.now(timezone.utc)
        ):
            product.status = ProductStatus.closed
            raise ValidationError("product_batch_closed")

        if fulfillment_type == Order.FulfillmentType.delivery and not delivery_address:
            raise ValidationError("delivery_address_required")

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

        # Если партия уже в режиме добора 24ч (кто-то достиг порога раньше),
        # уведомим текущего пользователя при оформлении заказа, чтобы он понимал статус.
        if product.status == ProductStatus.waiting_24h and not threshold_reached_now:
            should_notify_threshold_for_user = True

        await clear_cart_item(session, user_id=user_id, product_id=product_id)
        await session.flush()

    logger.info("order.created", extra={"order_id": order.id, "user_id": user_id, "product_id": product_id})
    await send_admin_notification(
        f"🧾 Новый заказ #{order.id}: пользователь {user_id}, товар {product_id}, вес {order.weight_total} кг"
    )

    # Отправка в админ-группу в отдельную тему (если это форум)
    try:
        prod_name = product.name if product else f"Товар #{product_id}"
        current_total = int(product.total_weight or 0) if product else 0
        current_price = price_per_kg(current_total)
        est_sum = int(order.weight_total) * int(current_price)
        remaining_to_min = max(0, int(product.min_weight or 0) - current_total) if product else 0
        remaining_to_next = next_tier_remaining(current_total)
        tier_label = tier_label_ru(current_total)
        title = f"Заказ #{order.id} • {prod_name}"
        address = html.escape(order.delivery_address) if order.delivery_address else ""
        comment_safe = html.escape(order.comment) if order.comment else ""
        name_safe = html.escape(prod_name)
        user_line = (" ".join([user.first_name or "", f"@{user.username}" if user.username else ""]).strip()) or f"User #{user_id}"
        messages = [
            "\n".join(
                [
                    f"🧾 <b>Поступил заказ #{order.id}</b>",
                    f"Товар: <b>{name_safe}</b> (#{product_id})",
                    f"Вес: <b>{order.weight_total} кг</b>",
                    f"Получение: <b>{fulfillment_label_bilingual(order.fulfillment_type)}</b>",
                    (f"Адрес: <b>{address}</b>" if address else ""),
                    (f"Комментарий: {comment_safe}" if comment_safe else ""),
                    "",
                    f"👤 Клиент: {html.escape(user_line)}",
                    (f"📞 Телефон: {user.phone}" if user.phone else ""),
                ]
            ).strip(),
            "\n".join(
                [
                    "📊 <b>Сводка по партии</b>",
                    f"Собрано: <b>{current_total} кг</b>",
                    (f"До порога: <b>{remaining_to_min} кг</b>" if remaining_to_min else "Порог достигнут — идёт добор 24ч."),
                    f"Текущий уровень: <b>{tier_label}</b>",
                    (f"До следующего уровня: <b>{remaining_to_next} кг</b>" if remaining_to_next else "Достигнут максимальный уровень цены."),
                    f"Цена сейчас: <b>{format_sum(current_price)} сум/кг</b>",
                    f"Оценка суммы заказа: <b>{format_sum(est_sum)} сум</b>",
                ]
            ),
        ]
        await send_admin_forum_topic(title=title, messages=messages)
    except Exception:
        logger.exception("admin_forum_order_notification_failed", extra={"order_id": order.id})

    # Дублируем в личку админу (если настроен ADMIN_TELEGRAM_USER_ID)
    try:
        prod_name = product.name if product else f"Товар #{product_id}"
        current_total = int(product.total_weight or 0) if product else 0
        current_price = price_per_kg(current_total)
        est_sum = int(order.weight_total) * int(current_price)
        dm_text = "\n".join(
            [
                f"🧾 Заказ #{order.id}",
                f"Товар: {prod_name} (#{product_id})",
                f"Вес: {order.weight_total} кг",
                f"Получение: {fulfillment_label_bilingual(order.fulfillment_type)}",
                (f"Адрес: {order.delivery_address}" if order.delivery_address else ""),
                (f"Комментарий: {order.comment}" if order.comment else ""),
                "",
                f"Собрано по партии: {current_total} кг",
                f"Цена сейчас: {format_sum(current_price)} сум/кг",
                f"Сумма (оценка): {format_sum(est_sum)} сум",
            ]
        ).strip()
        await send_admin_dm(dm_text)
    except Exception:
        logger.exception("admin_dm_order_notification_failed", extra={"order_id": order.id})

    # Уведомление пользователя о заказе
    if user.telegram_id:
        user_lang = normalize_lang(user.language)
        await send_user_notification(
            user.telegram_id,
            t("order_created", user_lang, product_id=product_id, weight_total=order.weight_total),
        )

    # Если только что достигли порога 100 кг — уведомляем всех участников партии
    if threshold_reached_now:
        stmt = select(User.telegram_id, User.language).join(Order, Order.user_id == User.id).where(
            Order.product_id == product_id
        )
        rows = (await session.execute(stmt)).all()
        notified_ids: set[int] = set()
        recipients: list[tuple[int, str]] = []
        for tg_id, language in rows:
            if tg_id and tg_id not in notified_ids:
                notified_ids.add(tg_id)
                recipients.append((int(tg_id), t("threshold_reached", language)))
        ok, fail = await send_user_notifications_batch(recipients, kind="threshold_reached", per_message_delay_s=0.08)
        await send_admin_notification(
            f"🎉 Партия #{product_id} достигла порога. Уведомления: {ok} ok / {fail} fail"
        )
    elif should_notify_threshold_for_user and user.telegram_id:
        user_lang = normalize_lang(user.language)
        await send_user_notification(
            int(user.telegram_id),
            t("threshold_reached", user_lang),
        )

    if scheduler is not None and should_schedule_product_id is not None and schedule_at is not None:
        schedule_close_product(scheduler, product_id=int(should_schedule_product_id), run_at=schedule_at)
        cancel_collection_end_product(scheduler, product_id=int(should_schedule_product_id))
        logger.info(
            "scheduler.job_scheduled",
            extra={"job_id": f"close_product:{should_schedule_product_id}", "product_id": should_schedule_product_id},
        )

    return order

