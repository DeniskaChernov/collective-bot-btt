from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import create_engine, create_sessionmaker
from app.i18n import t
from app.models import Order, Product, ProductStatus, User
from app.services.scheduler import schedule_close_product, schedule_collection_end_product
from app.notifications import send_admin_notification, send_user_notification

logger = logging.getLogger(__name__)


def create_scheduler(settings: Settings) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
    scheduler.add_jobstore(SQLAlchemyJobStore(url=settings.scheduler_jobstore_url))
    return scheduler


async def recover_scheduler_jobs(*, session: AsyncSession, scheduler: AsyncIOScheduler) -> None:
    now = datetime.now(timezone.utc)
    stmt = (
        select(Product.id, Product.threshold_reached_at)
        .where(Product.status == ProductStatus.waiting_24h)
        .where(Product.threshold_reached_at.is_not(None))
    )
    rows = (await session.execute(stmt)).all()
    for product_id, reached_at in rows:
        if reached_at is None:
            continue
        run_at = reached_at + timedelta(hours=24)
        if run_at < now:
            run_at = now + timedelta(seconds=1)
        schedule_close_product(scheduler, product_id=int(product_id), run_at=run_at)

    # Восстановить задачи «конец 3-дневного окна» для открытых партий
    stmt2 = (
        select(Product.id, Product.collection_until)
        .where(Product.status == ProductStatus.open)
        .where(Product.collection_until.is_not(None))
        .where(Product.collection_until > now)
    )
    for product_id, until in (await session.execute(stmt2)).all():
        if until:
            schedule_collection_end_product(scheduler, product_id=int(product_id), run_at=until)


async def close_product_job(*, product_id: int) -> None:
    """
    APScheduler persistent job entrypoint.
    Must be module-level importable for SQLAlchemyJobStore.
    """
    settings = get_settings()
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)

    async with sessionmaker() as session:
        await _close_product_if_due(session=session, product_id=product_id)

    await engine.dispose()


async def _close_product_if_due(*, session: AsyncSession, product_id: int) -> None:
    now = datetime.now(timezone.utc)
    async with session.begin():
        product = (
            await session.execute(
                select(Product)
                .where(Product.id == product_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if product is None:
            logger.warning("scheduler.product_not_found", extra={"product_id": product_id})
            return
        if product.status != ProductStatus.waiting_24h:
            return
        if product.threshold_reached_at is None:
            logger.warning("scheduler.missing_threshold_reached_at", extra={"product_id": product_id})
            return
        if product.threshold_reached_at + timedelta(hours=24) > now:
            return
        product.status = ProductStatus.closed
        logger.info("product.closed", extra={"product_id": product_id, "source": "scheduler"})

        # Уведомляем всех участников партии
        stmt = select(User.telegram_id, User.language).join(Order, Order.user_id == User.id).where(
            Order.product_id == product_id
        )
        rows = (await session.execute(stmt)).all()
        notified_ids: set[int] = set()
        for tg_id, language in rows:
            if tg_id and tg_id not in notified_ids:
                notified_ids.add(tg_id)
                await send_user_notification(
                    int(tg_id),
                    t("batch_closed", language),
                )

    await send_admin_notification(f"🚀 Партия #{product_id} закрыта (таймер 24ч истёк)")


async def collection_end_job(*, product_id: int) -> None:
    """
    Конец 3-дневного окна набора заказов.
    Если партия ещё open и не набрала min_weight — закрываем.
    """
    settings = get_settings()
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    async with sessionmaker() as session:
        await _collection_end_if_due(session=session, product_id=product_id)
    await engine.dispose()


async def _collection_end_if_due(*, session: AsyncSession, product_id: int) -> None:
    total_weight = min_weight = 0
    async with session.begin():
        product = (
            await session.execute(
                select(Product).where(Product.id == product_id).with_for_update()
            )
        ).scalar_one_or_none()
        if product is None:
            logger.warning("scheduler.collection_end_product_not_found", extra={"product_id": product_id})
            return
        if product.status != ProductStatus.open:
            return
        if product.collection_until is None:
            return
        if product.total_weight >= product.min_weight:
            return
        total_weight = product.total_weight
        min_weight = product.min_weight
        product.status = ProductStatus.closed
        logger.info(
            "product.closed",
            extra={"product_id": product_id, "source": "scheduler", "reason": "collection_window_ended"},
        )
    await send_admin_notification(
        f"⏱ Партия #{product_id} закрыта: 3 дня истекли, набрано {total_weight} кг (порог {min_weight} кг)."
    )

