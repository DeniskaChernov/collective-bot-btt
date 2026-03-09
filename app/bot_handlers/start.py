from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot_handlers.keyboards import language_select_kb, main_menu_kb, phone_request_kb
from app.i18n import normalize_lang, t
from app.services.users import get_or_create_user_by_telegram_id, set_user_language

router = Router()


LANGUAGE_CHOICES = {
    "RU": "ru",
    "UZ": "uz",
    "🇷🇺 RU": "ru",
    "🇺🇿 UZ": "uz",
}


async def _get_current_user(message: Message, session: AsyncSession):
    tg_user = message.from_user
    user = await get_or_create_user_by_telegram_id(
        session,
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )
    await session.commit()
    return user


@router.message(CommandStart())
async def start(message: Message, session: AsyncSession):
    user = await _get_current_user(message, session)
    lang = normalize_lang(user.language)
    if not user.language:
        await message.answer(t("choose_language"), reply_markup=language_select_kb())
        return
    if user.phone:
        await message.answer(
            t("welcome_registered", lang),
            reply_markup=main_menu_kb(lang),
        )
        return
    await message.answer(
        t("welcome_need_phone", lang),
        reply_markup=phone_request_kb(lang),
    )


@router.message(F.text == "Меню")
@router.message(F.text == "Menu")
@router.message(F.text == "Menyu")
async def menu(message: Message, session: AsyncSession):
    user = await _get_current_user(message, session)
    lang = normalize_lang(user.language)
    await message.answer(t("menu_choose_action", lang), reply_markup=main_menu_kb(lang))


@router.message(F.text == "📱 Каталог и заказы в приложении")
@router.message(F.text == "📱 Открыть приложение")
@router.message(F.text == "📱 Ilovani ochish")
async def open_app_fallback(message: Message, session: AsyncSession):
    user = await _get_current_user(message, session)
    lang = normalize_lang(user.language)
    await message.answer(
        t("open_app_fallback", lang),
        reply_markup=main_menu_kb(lang),
    )


@router.message(F.text == "🌐 Сменить язык")
@router.message(F.text == "🌐 Tilni o'zgartirish")
async def choose_language(message: Message, session: AsyncSession):
    await _get_current_user(message, session)
    await message.answer(t("choose_language"), reply_markup=language_select_kb())


@router.message(lambda m: (m.text or "").strip().upper() in LANGUAGE_CHOICES)
async def set_language(message: Message, session: AsyncSession):
    user = await _get_current_user(message, session)
    selected_lang = LANGUAGE_CHOICES[(message.text or "").strip().upper()]
    await set_user_language(session, user_id=user.id, language=selected_lang)
    await session.commit()
    if user.phone:
        await message.answer(
            f"{t('language_changed', selected_lang)}\n\n{t('welcome_registered', selected_lang)}",
            reply_markup=main_menu_kb(selected_lang),
        )
        return
    await message.answer(
        t("language_saved_need_phone", selected_lang),
        reply_markup=phone_request_kb(selected_lang),
    )


@router.message(F.text)
async def unknown_message(message: Message, session: AsyncSession):
    user = await _get_current_user(message, session)
    if not user.language:
        await message.answer(t("choose_language"), reply_markup=language_select_kb())
        return
    lang = normalize_lang(user.language)
    await message.answer(
        t("unknown_message", lang),
        reply_markup=main_menu_kb(lang),
    )

