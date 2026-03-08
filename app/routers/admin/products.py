from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.product import ProductCreateIn, ProductOut, ProductUpdateIn
from app.schemas.response import ok
from app.security.admin import require_admin
from app.security.rate_limit import admin_rate_limit
from app.services.products import (
    create_product,
    get_product,
    list_products,
    manual_cancel_product,
    manual_close_product,
    manual_reopen_product,
    update_product,
)
from app.services.scheduler import cancel_close_product, cancel_collection_end_product, schedule_collection_end_product

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/products",
    tags=["admin-products"],
    dependencies=[Depends(require_admin), Depends(admin_rate_limit)],
)


def _scheduler(request: Request) -> AsyncIOScheduler:
    return request.app.state.scheduler


@router.get("")
async def admin_list_products(session: AsyncSession = Depends(get_db)):
    products = await list_products(session)
    return ok([ProductOut.model_validate(p) for p in products])


@router.post("")
async def admin_create_product(payload: ProductCreateIn, request: Request, session: AsyncSession = Depends(get_db)):
    product = await create_product(
        session,
        article=payload.article,
        name=payload.name,
        profile=payload.profile,
        image_url=payload.image_url.strip() if payload.image_url else None,
        thread_width=payload.thread_width.strip() if payload.thread_width else None,
        color=payload.color.strip() if payload.color else None,
        min_weight=payload.min_weight,
        max_weight_per_order=payload.max_weight_per_order,
    )
    if product.collection_until:
        schedule_collection_end_product(
            _scheduler(request),
            product_id=product.id,
            run_at=product.collection_until,
        )
    return ok(ProductOut.model_validate(product))


@router.get("/{product_id}")
async def admin_get_product(product_id: int, session: AsyncSession = Depends(get_db)):
    product = await get_product(session, product_id=product_id)
    return ok(ProductOut.model_validate(product))


@router.patch("/{product_id}")
async def admin_update_product(payload: ProductUpdateIn, product_id: int, session: AsyncSession = Depends(get_db)):
    product = await update_product(
        session,
        product_id=product_id,
        article=payload.article,
        name=payload.name,
        profile=payload.profile,
        image_url=payload.image_url,
        thread_width=payload.thread_width.strip() if payload.thread_width else None,
        color=payload.color.strip() if payload.color else None,
        min_weight=payload.min_weight,
        max_weight_per_order=payload.max_weight_per_order,
    )
    return ok(ProductOut.model_validate(product))


@router.post("/{product_id}/close")
async def admin_manual_close(product_id: int, request: Request, session: AsyncSession = Depends(get_db)):
    product = await manual_close_product(session, product_id=product_id)
    sched = _scheduler(request)
    cancel_close_product(sched, product_id=product_id)
    cancel_collection_end_product(sched, product_id=product_id)
    logger.info(
        "scheduler.job_cancelled",
        extra={"job_id": f"close_product:{product_id}", "product_id": product_id},
    )
    return ok(ProductOut.model_validate(product))


@router.post("/{product_id}/reopen")
async def admin_manual_reopen(product_id: int, request: Request, session: AsyncSession = Depends(get_db)):
    product = await manual_reopen_product(session, product_id=product_id)
    sched = _scheduler(request)
    cancel_close_product(sched, product_id=product_id)
    if product.collection_until:
        schedule_collection_end_product(sched, product_id=product_id, run_at=product.collection_until)
    return ok(ProductOut.model_validate(product))


@router.post("/{product_id}/cancel")
async def admin_manual_cancel(product_id: int, request: Request, session: AsyncSession = Depends(get_db)):
    """Отменить партию (статус cancelled). Заказы не меняются."""
    product = await manual_cancel_product(session, product_id=product_id)
    sched = _scheduler(request)
    cancel_close_product(sched, product_id=product_id)
    cancel_collection_end_product(sched, product_id=product_id)
    logger.info(
        "scheduler.jobs_cancelled_for_product",
        extra={"product_id": product_id},
    )
    return ok(ProductOut.model_validate(product))

