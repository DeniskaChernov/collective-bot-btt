from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot_handlers.keyboards import inline_open_app_kb
from app.i18n import t

router = Router()


@router.callback_query(F.data == "back:catalog")
async def back_to_catalog(callback: CallbackQuery, session: AsyncSession) -> None:  # noqa: ARG001
    await callback.message.edit_text(
        f"{t('menu_choose_action', 'ru')} / {t('menu_choose_action', 'uz')}",
        reply_markup=inline_open_app_kb(),
    )
    await callback.answer()
