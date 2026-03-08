from __future__ import annotations

import logging

from aiogram.types import Update
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import Settings

logger = logging.getLogger(__name__)


def build_telegram_router(*, settings: Settings) -> APIRouter:
    router = APIRouter(tags=["telegram"])

    @router.post(settings.telegram_webhook_path)
    async def telegram_webhook(request: Request):
        bot = request.app.state.bot
        dp = request.app.state.dp
        if settings.telegram_secret_token:
            header_token = request.headers.get("x-telegram-bot-api-secret-token")
            if header_token != settings.telegram_secret_token:
                return JSONResponse(status_code=403, content={"ok": False})

        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
        return {"ok": True}

    return router

