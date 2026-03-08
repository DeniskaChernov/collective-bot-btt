from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


async def send_admin_notification(text: str) -> None:
    settings = get_settings()
    chat_id = settings.admin_telegram_chat_id
    if not chat_id:
        return
    from app.bot import create_bot
    bot = create_bot(settings)
    try:
        await bot.send_message(chat_id, text)
    except Exception:
        logger.exception("admin_notification_failed")
    finally:
        await bot.session.close()


async def send_user_notification(telegram_id: int, text: str) -> None:
    settings = get_settings()
    from app.bot import create_bot
    bot = create_bot(settings)
    try:
        await bot.send_message(telegram_id, text)
    except Exception:
        logger.exception("user_notification_failed")
    finally:
        await bot.session.close()

