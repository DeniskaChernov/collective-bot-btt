from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import MenuButtonWebApp, WebAppInfo
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot_handlers.catalog import router as catalog_router
from app.bot_handlers.contacts import router as contacts_router
from app.bot_handlers.middlewares import DbSessionMiddleware
from app.bot_handlers.start import router as start_router
from app.config import Settings

logger = logging.getLogger(__name__)


def create_bot(settings: Settings) -> Bot:
    return Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(sessionmaker: async_sessionmaker[AsyncSession]) -> Dispatcher:
    dp = Dispatcher()
    dp.message.middleware(DbSessionMiddleware(sessionmaker))
    dp.include_router(start_router)
    dp.include_router(contacts_router)
    dp.include_router(catalog_router)
    return dp


async def ensure_webhook(bot: Bot, settings: Settings) -> None:
    if not settings.webhook_base_url:
        logger.warning(
            "telegram.webhook_skipped",
            extra={"reason": "WEBHOOK_BASE_URL is not set — bot will not receive updates"},
        )
        return
    url = settings.webhook_base_url.rstrip("/") + settings.telegram_webhook_path
    await bot.set_webhook(
        url=url,
        secret_token=settings.telegram_secret_token,
        drop_pending_updates=False,
    )
    logger.info("telegram.webhook_set", extra={"url": url})

    # Кнопка меню бота (рядом с полем ввода) — всегда открывает наш Mini App
    mini_app_url = settings.webhook_base_url.rstrip("/") + "/mini-app/"
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Открыть приложение", web_app=WebAppInfo(url=mini_app_url))
        )
        logger.info("telegram.menu_button_set", extra={"url": mini_app_url})
    except Exception as e:
        logger.warning("telegram.menu_button_failed", extra={"error": str(e)})

