from __future__ import annotations

import json
from typing import Annotated
from urllib.parse import urlparse

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import Response
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database import get_db
from app.models import Order, ProductStatus
from app.schemas.cart import CartItemOut, CartOut
from app.schemas.order import OrderCreateIn, OrderOut
from app.schemas.product import ProductOut
from app.schemas.response import ok
from app.schemas.user import MeOut
from app.security.telegram_webapp import verify_init_data
from app.services.cart import add_to_cart_5kg, get_cart, remove_from_cart_5kg
from app.services.orders import create_order_from_cart
from app.services.products import list_products
from app.services.users import get_or_create_user_by_telegram_id, get_user

router = APIRouter(prefix="/public", tags=["public"])


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _scheduler(request: Request) -> AsyncIOScheduler:
    return request.app.state.scheduler


async def current_user_id(
    request: Request,
    session: AsyncSession = Depends(get_db),
    x_telegram_init_data: Annotated[str | None, Header(alias="X-Telegram-Init-Data")] = None,
) -> int:
    if not x_telegram_init_data:
        raise ValueError("Missing X-Telegram-Init-Data")
    parsed = verify_init_data(x_telegram_init_data, bot_token=_settings(request).telegram_bot_token)
    user_raw = parsed.get("user")
    if not user_raw:
        raise ValueError("Missing user in initData")
    user_obj = json.loads(user_raw)
    telegram_id = int(user_obj["id"])
    first_name = user_obj.get("first_name")
    username = user_obj.get("username")
    async with session.begin():
        user = await get_or_create_user_by_telegram_id(
            session,
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=user_obj.get("last_name"),
        )
    return int(user.id)


async def current_user(
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_db),
):
    return await get_user(session, user_id=user_id)


@router.get("/me")
async def me(user=Depends(current_user)):
    phone_masked = None
    if user.phone and len(user.phone) >= 4:
        phone_masked = "*" * (len(user.phone) - 4) + user.phone[-4:]
    return ok(
        MeOut(
            id=user.id,
            first_name=user.first_name,
            username=user.username,
            has_phone=bool(user.phone),
            phone_masked=phone_masked,
    )
)


@router.get("/products")
async def products(session: AsyncSession = Depends(get_db)):
    products_ = await list_products(session)
    products_ = [p for p in products_ if p.status != ProductStatus.cancelled]
    return ok([ProductOut.model_validate(p) for p in products_])


@router.get("/proxy-image")
async def proxy_image(url: str):
    """Прокси для картинок по ссылке (Яндекс.Диск и др.): сервер качает файл и отдаёт в приложение."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return Response(status_code=400, content=b"Invalid URL")
    headers = {}
    if "yandex" in parsed.netloc.lower():
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0"
        headers["Referer"] = "https://disk.yandex.ru/"
        headers["Accept"] = "image/webp,image/apng,image/*,*/*;q=0.8"
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            body = r.content
            if len(body) > 10 * 1024 * 1024:
                return Response(status_code=413, content=b"Image too large")
            content_type = r.headers.get("content-type", "application/octet-stream").split(";")[0].strip()
            if not content_type.startswith("image/"):
                content_type = "image/jpeg"
            return Response(content=body, media_type=content_type)
    except httpx.HTTPError:
        return Response(status_code=502, content=b"Upstream error")
    except Exception:
        return Response(status_code=502, content=b"Proxy error")


@router.get("/cart")
async def cart(user_id: int = Depends(current_user_id), session: AsyncSession = Depends(get_db)):
    items = await get_cart(session, user_id=user_id)
    return ok(CartOut(items=[CartItemOut(product_id=i.product_id, weight=i.weight) for i in items]))


@router.post("/cart/{product_id}/add5")
async def cart_add5(product_id: int, user_id: int = Depends(current_user_id), session: AsyncSession = Depends(get_db)):
    item = await add_to_cart_5kg(session, user_id=user_id, product_id=product_id)
    return ok(CartItemOut(product_id=item.product_id, weight=item.weight))


@router.post("/cart/{product_id}/remove5")
async def cart_remove5(
    product_id: int, user_id: int = Depends(current_user_id), session: AsyncSession = Depends(get_db)
):
    item = await remove_from_cart_5kg(session, user_id=user_id, product_id=product_id)
    if item is None:
        return ok(None)
    return ok(CartItemOut(product_id=item.product_id, weight=item.weight))


@router.post("/orders/{product_id}")
async def order_create(
    product_id: int,
    request: Request,
    payload: OrderCreateIn,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_db),
):
    order = await create_order_from_cart(
        session,
        scheduler=_scheduler(request),
        user_id=user_id,
        product_id=product_id,
        fulfillment_type=payload.fulfillment_type,
        delivery_address=payload.delivery_address,
        comment=payload.comment,
    )
    return ok(OrderOut.model_validate(order))


@router.get("/orders")
async def my_orders(
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(desc(Order.created_at))
    )
    result = await session.execute(stmt)
    orders = result.scalars().all()
    return ok([OrderOut.model_validate(o) for o in orders])

