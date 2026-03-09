from __future__ import annotations

from aiogram import Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot_handlers.keyboards import main_menu_kb
from app.i18n import normalize_lang, t
from app.notifications import send_admin_notification
from app.services.users import get_or_create_user_by_telegram_id, set_user_phone

router = Router()


@router.message(lambda m: m.contact is not None)
async def contact(message: Message, session: AsyncSession):
    contact = message.contact
    if contact is None:
        return
    tg_user = message.from_user
    user = await get_or_create_user_by_telegram_id(
        session,
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )
    await set_user_phone(session, user_id=user.id, phone=contact.phone_number)
    await session.commit()
    lang = normalize_lang(user.language)
    await message.answer(
        t("registration_done", lang),
        reply_markup=main_menu_kb(lang),
    )
    await send_admin_notification(f"👤 Новый клиент: @{tg_user.username or ''} ({contact.phone_number})")

