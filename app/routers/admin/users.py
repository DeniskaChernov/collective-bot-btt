from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Order, User
from app.schemas.response import ok
from app.schemas.user import UserOut, UserWithStatsOut
from app.security.admin import require_admin
from app.security.rate_limit import admin_rate_limit

router = APIRouter(
    prefix="/admin/users",
    tags=["admin-users"],
    dependencies=[Depends(require_admin), Depends(admin_rate_limit)],
)


@router.get("")
async def list_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    phone: str | None = Query(default=None),
    username: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(User)
    if phone:
        stmt = stmt.where(User.phone.ilike(f"%{phone}%"))
    if username:
        stmt = stmt.where(User.username.ilike(f"%{username}%"))
    stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
    users = (await session.execute(stmt)).scalars().all()
    return ok([UserOut.model_validate(u) for u in users])


@router.get("/{user_id}")
async def get_user_details(user_id: int, session: AsyncSession = Depends(get_db)):
    user = (await session.get(User, user_id))
    if user is None:
        from app.errors import NotFound

        raise NotFound("User not found", details={"user_id": user_id})

    agg_stmt = select(
        func.count(Order.id),
        func.coalesce(func.sum(Order.weight_total), 0),
    ).where(Order.user_id == user_id)
    total_orders, total_weight = (await session.execute(agg_stmt)).one()

    base = UserOut.model_validate(user)
    return ok(
        UserWithStatsOut(
            **base.model_dump(),
            total_orders=int(total_orders or 0),
            total_weight=int(total_weight or 0),
        )
    )

