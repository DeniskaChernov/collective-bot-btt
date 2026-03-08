from __future__ import annotations

from datetime import datetime

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.base import ConflictingIdError
from apscheduler.schedulers.asyncio import AsyncIOScheduler


def close_product_job_id(product_id: int) -> str:
    return f"close_product:{product_id}"


def collection_end_job_id(product_id: int) -> str:
    return f"collection_end:{product_id}"


def schedule_close_product(
    scheduler: AsyncIOScheduler,
    *,
    product_id: int,
    run_at: datetime,
) -> None:
    job_id = close_product_job_id(product_id)
    if scheduler.get_job(job_id) is not None:
        return
    try:
        scheduler.add_job(
            "app.scheduler_runtime:close_product_job",
            trigger="date",
            id=job_id,
            replace_existing=False,
            run_date=run_at,
            kwargs={"product_id": product_id},
            misfire_grace_time=60 * 30,
            coalesce=True,
            max_instances=1,
        )
    except ConflictingIdError:
        return


def cancel_close_product(scheduler: AsyncIOScheduler, *, product_id: int) -> None:
    job_id = close_product_job_id(product_id)
    try:
        scheduler.remove_job(job_id)
    except JobLookupError:
        return


def schedule_collection_end_product(
    scheduler: AsyncIOScheduler,
    *,
    product_id: int,
    run_at: datetime,
) -> None:
    """Запланировать закрытие партии в конце 3-дневного окна (если не набрали min_weight)."""
    job_id = collection_end_job_id(product_id)
    if scheduler.get_job(job_id) is not None:
        return
    try:
        scheduler.add_job(
            "app.scheduler_runtime:collection_end_job",
            trigger="date",
            id=job_id,
            replace_existing=False,
            run_date=run_at,
            kwargs={"product_id": product_id},
            misfire_grace_time=60 * 30,
            coalesce=True,
            max_instances=1,
        )
    except ConflictingIdError:
        return


def cancel_collection_end_product(scheduler: AsyncIOScheduler, *, product_id: int) -> None:
    job_id = collection_end_job_id(product_id)
    try:
        scheduler.remove_job(job_id)
    except JobLookupError:
        return

