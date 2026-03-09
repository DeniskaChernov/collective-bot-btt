from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.i18n import normalize_lang, order_status_text, t
from app.models import Order
from app.notifications import send_user_notification
from app.schemas.order import AdminOrderOut, OrderOut, OrderStatusUpdateIn
from app.schemas.response import ok
from app.security.admin import require_admin
from app.security.rate_limit import admin_rate_limit

router = APIRouter(
    prefix="/admin/orders",
    tags=["admin-orders"],
    dependencies=[Depends(require_admin), Depends(admin_rate_limit)],
)


def _order_to_admin_out(order: Order) -> AdminOrderOut:
    user = order.user
    telegram_id = user.telegram_id if user else None
    username = user.username if user else None
    telegram_link = None
    if telegram_id:
        telegram_link = f"https://t.me/{username}" if username else f"tg://user?id={telegram_id}"
    return AdminOrderOut(
        id=order.id,
        user_id=order.user_id,
        product_id=order.product_id,
        weight_total=order.weight_total,
        status=order.status,
        fulfillment_type=order.fulfillment_type,
        delivery_address=order.delivery_address,
        comment=order.comment,
        created_at=order.created_at,
        user_phone=user.phone if user else None,
        user_telegram_id=int(telegram_id) if telegram_id else None,
        user_username=username,
        user_first_name=user.first_name if user else None,
        telegram_link=telegram_link,
    )


@router.get("")
async def list_orders(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: Order.OrderStatus | None = Query(default=None),
    fulfillment_type: Order.FulfillmentType | None = Query(default=None),
    product_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Order).options(selectinload(Order.user))
    conditions = []
    if status is not None:
        conditions.append(Order.status == status)
    if fulfillment_type is not None:
        conditions.append(Order.fulfillment_type == fulfillment_type)
    if product_id is not None:
        conditions.append(Order.product_id == product_id)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(desc(Order.created_at)).limit(limit).offset(offset)
    orders = list((await session.execute(stmt)).scalars().all())
    return ok([_order_to_admin_out(o) for o in orders])


@router.post("/bulk-confirm-by-product")
async def bulk_confirm_pending_by_product(
    product_id: int = Query(..., description="ID партии (товара)"),
    session: AsyncSession = Depends(get_db),
):
    """Подтвердить все заказы со статусом «Ожидает» по указанной партии."""
    stmt = select(Order).where(
        Order.product_id == product_id,
        Order.status == Order.OrderStatus.pending,
    ).options(selectinload(Order.user))
    result = await session.execute(stmt)
    orders = list(result.scalars().all())
    updated = 0
    async with session.begin():
        for order in orders:
            order.status = Order.OrderStatus.confirmed
            updated += 1
            if order.user and order.user.telegram_id:
                lang = normalize_lang(order.user.language)
                await send_user_notification(
                    int(order.user.telegram_id),
                    t("order_confirmed", lang, order_id=order.id),
                )
        await session.flush()
    return ok({"updated": updated, "order_ids": [o.id for o in orders]})


@router.get("/{order_id}")
async def get_order(order_id: int, session: AsyncSession = Depends(get_db)):
    order = await session.get(Order, order_id, options=[selectinload(Order.user)])
    if order is None:
        from app.errors import NotFound

        raise NotFound("Order not found", details={"order_id": order_id})
    return ok(_order_to_admin_out(order))


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: int,
    payload: OrderStatusUpdateIn,
    session: AsyncSession = Depends(get_db),
):
    from app.errors import NotFound

    async with session.begin():
        order = await session.get(Order, order_id, options=[selectinload(Order.user)])
        if order is None:
            raise NotFound("Order not found", details={"order_id": order_id})
        order.status = payload.status
        await session.flush()
        user = order.user
        telegram_id = user.telegram_id if user else None

    if telegram_id:
        lang = normalize_lang(user.language if user else None)
        status_text = order_status_text(payload.status.value, lang)
        await send_user_notification(
            telegram_id,
            t("order_status_changed", lang, order_id=order_id, status_text=status_text),
        )
    order = await session.get(Order, order_id, options=[selectinload(Order.user)])
    return ok(_order_to_admin_out(order))


@router.post("/{order_id}/cancel")
async def cancel_order(order_id: int, session: AsyncSession = Depends(get_db)):
    from app.errors import NotFound

    async with session.begin():
        order = await session.get(Order, order_id, options=[selectinload(Order.user)])
        if order is None:
            raise NotFound("Order not found", details={"order_id": order_id})
        order.status = Order.OrderStatus.cancelled
        await session.flush()
        user = order.user
        telegram_id = user.telegram_id if user else None

    if telegram_id:
        lang = normalize_lang(user.language if user else None)
        await send_user_notification(
            telegram_id,
            t("order_cancelled", lang, order_id=order_id),
        )
    order = await session.get(Order, order_id, options=[selectinload(Order.user)])
    return ok(_order_to_admin_out(order))

