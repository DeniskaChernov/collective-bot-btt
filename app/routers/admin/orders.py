from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Order
from app.notifications import send_user_notification
from app.schemas.order import OrderOut, OrderStatusUpdateIn
from app.schemas.response import ok
from app.security.admin import require_admin
from app.security.rate_limit import admin_rate_limit

router = APIRouter(
    prefix="/admin/orders",
    tags=["admin-orders"],
    dependencies=[Depends(require_admin), Depends(admin_rate_limit)],
)


@router.get("")
async def list_orders(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: Order.OrderStatus | None = Query(default=None),
    fulfillment_type: Order.FulfillmentType | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Order)
    conditions = []
    if status is not None:
        conditions.append(Order.status == status)
    if fulfillment_type is not None:
        conditions.append(Order.fulfillment_type == fulfillment_type)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(desc(Order.created_at)).limit(limit).offset(offset)
    orders = list((await session.execute(stmt)).scalars().all())
    return ok([OrderOut.model_validate(o) for o in orders])


@router.get("/{order_id}")
async def get_order(order_id: int, session: AsyncSession = Depends(get_db)):
    order = await session.get(Order, order_id)
    if order is None:
        from app.errors import NotFound

        raise NotFound("Order not found", details={"order_id": order_id})
    return ok(OrderOut.model_validate(order))


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: int,
    payload: OrderStatusUpdateIn,
    session: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload

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
        status_text = {
            Order.OrderStatus.pending: "ожидает",
            Order.OrderStatus.confirmed: "подтверждён",
            Order.OrderStatus.cancelled: "отменён",
            Order.OrderStatus.completed: "выполнен",
        }.get(payload.status, payload.status.value)
        await send_user_notification(
            telegram_id,
            f"📦 Заказ #{order_id}: статус изменён на «{status_text}».",
        )
    async with session.begin():
        order = await session.get(Order, order_id)
    return ok(OrderOut.model_validate(order))


@router.post("/{order_id}/cancel")
async def cancel_order(order_id: int, session: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload

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
        await send_user_notification(
            telegram_id,
            f"❌ Заказ #{order_id} отменён.",
        )
    async with session.begin():
        order = await session.get(Order, order_id)
    return ok(OrderOut.model_validate(order))

