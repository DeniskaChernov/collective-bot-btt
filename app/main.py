from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.bot import create_bot, create_dispatcher, ensure_webhook
from app.config import get_settings
from app.database import create_engine, create_sessionmaker
from app.errors import AppError, Conflict, Forbidden, NotFound, ValidationError
from app.logging import configure_logging
from app.routers.admin.auth import router as admin_auth_router
from app.routers.admin.orders import router as admin_orders_router
from app.routers.admin.products import router as admin_products_router
from app.routers.admin.users import router as admin_users_router
from app.routers.public import router as public_router
from app.routers.telegram import build_telegram_router
from app.schemas.response import err, ok
from app.scheduler_runtime import create_scheduler, recover_scheduler_jobs
from app.security.rate_limit import FixedWindowRateLimiter
from app.models import Base

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)

    app.state.settings = settings
    app.state.admin_rate_limiter = FixedWindowRateLimiter()

    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    app.state.db_engine = engine
    app.state.db_sessionmaker = sessionmaker

    if os.environ.get("TESTING"):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    scheduler = create_scheduler(settings)
    app.state.scheduler = scheduler
    scheduler.start()

    async with sessionmaker() as session:
        await recover_scheduler_jobs(session=session, scheduler=scheduler)

    bot = create_bot(settings)
    dp = create_dispatcher(sessionmaker)
    app.state.bot = bot
    app.state.dp = dp

    await ensure_webhook(bot, settings)

    try:
        yield
    finally:
        try:
            scheduler.shutdown(wait=False)
        except Exception:
            logger.exception("scheduler.shutdown_failed")
        try:
            await bot.session.close()
        except Exception:
            logger.exception("bot.shutdown_failed")
        await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Collective Bot API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        status_code = 400
        if isinstance(exc, NotFound):
            status_code = 404
        elif isinstance(exc, Forbidden):
            status_code = 403
        elif isinstance(exc, Conflict):
            status_code = 409
        elif isinstance(exc, ValidationError):
            status_code = 400
        return JSONResponse(
            status_code=status_code,
            content=err(exc.code, exc.message, exc.details).model_dump(),
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(status_code=400, content=err("bad_request", str(exc)).model_dump())

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        logger.exception("unhandled_exception")
        return JSONResponse(status_code=500, content=err("internal_error", "Internal error").model_dump())

    @app.get("/health", tags=["health"])
    async def health():
        return ok(True)

    app.include_router(public_router)
    app.include_router(admin_auth_router)
    app.include_router(admin_products_router)
    app.include_router(admin_orders_router)
    app.include_router(admin_users_router)

    settings = get_settings()
    app.include_router(build_telegram_router(settings=settings))

    static_dir = Path(__file__).resolve().parent.parent / "static" / "mini-app"
    if static_dir.is_dir():
        app.mount("/mini-app", StaticFiles(directory=str(static_dir), html=True), name="mini-app")
    else:
        logger.warning("mini_app_static_dir_not_found", extra={"path": str(static_dir)})

    admin_ui_dir = Path(__file__).resolve().parent.parent / "static" / "admin"
    if admin_ui_dir.is_dir():
        app.mount("/admin-ui", StaticFiles(directory=str(admin_ui_dir), html=True), name="admin-ui")

    return app


app = create_app()

