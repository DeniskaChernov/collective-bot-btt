from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import create_engine, create_sessionmaker
from app.models import Order, Product, ProductStatus, User
from app.services.scheduler import schedule_close_product
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
                    "🚀 Партия закрыта.\n"
                    "Производство запущено. Ожидайте уведомление о готовности.",
                )

    await send_admin_notification(f"🚀 Партия #{product_id} закрыта (таймер 24ч истёк)")

