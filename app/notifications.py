from __future__ import annotations

import asyncio
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

MAX_SEND_ATTEMPTS = 3


async def _send_with_retries(
    bot,
    chat_id: int,
    text: str,
    *,
    kind: str,
    message_thread_id: int | None = None,
) -> bool:
    last_err: Exception | None = None
    for attempt in range(1, MAX_SEND_ATTEMPTS + 1):
        try:
            await bot.send_message(chat_id, text, message_thread_id=message_thread_id)
            return True
        except Exception as e:
            last_err = e
            # простая экспоненциальная пауза; aiogram сам умеет часть ретраев, но
            # это закрывает transient network errors/429 и т.п.
            delay = 0.6 * attempt
            logger.warning(
                "telegram.send_failed",
                extra={
                    "kind": kind,
                    "chat_id": chat_id,
                    "attempt": attempt,
                    "max_attempts": MAX_SEND_ATTEMPTS,
                    "error": str(e),
                },
            )
            await asyncio.sleep(delay)
    logger.exception(
        "telegram.send_gave_up",
        extra={"kind": kind, "chat_id": chat_id, "error": str(last_err) if last_err else None},
    )
    return False


async def send_admin_forum_topic(*, title: str, messages: list[str]) -> bool:
    """
    Создаёт тему (forum topic) в админ-группе и отправляет туда сообщения.
    Если чат не является форумом/нет прав — вернёт False.
    """
    settings = get_settings()
    chat_id = settings.admin_telegram_chat_id
    if not chat_id:
        return False
    if not messages:
        return True
    from app.bot import create_bot

    bot = create_bot(settings)
    try:
        try:
            topic = await bot.create_forum_topic(chat_id=int(chat_id), name=title)
        except Exception as e:
            logger.warning("telegram.forum_topic_create_failed", extra={"chat_id": chat_id, "error": str(e)})
            return False
        thread_id = getattr(topic, "message_thread_id", None)
        if not thread_id:
            return False
        ok_any = False
        for text in messages:
            sent = await _send_with_retries(
                bot,
                int(chat_id),
                text,
                kind="admin_forum",
                message_thread_id=int(thread_id),
            )
            ok_any = ok_any or sent
            await asyncio.sleep(0.05)
        return ok_any
    finally:
        await bot.session.close()


async def send_user_notifications_batch(
    recipients: list[tuple[int, str]],
    *,
    kind: str = "batch",
    per_message_delay_s: float = 0.05,
) -> tuple[int, int]:
    """
    Отправить пачку сообщений, переиспользуя один Bot и мягко троттля.
    Возвращает (ok_count, fail_count).
    """
    if not recipients:
        return (0, 0)
    settings = get_settings()
    from app.bot import create_bot

    bot = create_bot(settings)
    ok = 0
    fail = 0
    try:
        for telegram_id, text in recipients:
            sent = await _send_with_retries(bot, int(telegram_id), text, kind=kind)
            if sent:
                ok += 1
            else:
                fail += 1
            if per_message_delay_s > 0:
                await asyncio.sleep(per_message_delay_s)
    finally:
        await bot.session.close()
    return (ok, fail)


async def send_admin_notification(text: str) -> bool:
    settings = get_settings()
    chat_id = settings.admin_telegram_chat_id
    if not chat_id:
        return False
    from app.bot import create_bot
    bot = create_bot(settings)
    try:
        return await _send_with_retries(bot, int(chat_id), text, kind="admin")
    finally:
        await bot.session.close()


async def send_admin_dm(text: str) -> bool:
    settings = get_settings()
    user_id = settings.admin_telegram_user_id
    if not user_id:
        return False
    from app.bot import create_bot

    bot = create_bot(settings)
    try:
        return await _send_with_retries(bot, int(user_id), text, kind="admin_dm")
    finally:
        await bot.session.close()


async def send_user_notification(telegram_id: int, text: str) -> bool:
    settings = get_settings()
    from app.bot import create_bot
    bot = create_bot(settings)
    try:
        return await _send_with_retries(bot, int(telegram_id), text, kind="user")
    finally:
        await bot.session.close()

