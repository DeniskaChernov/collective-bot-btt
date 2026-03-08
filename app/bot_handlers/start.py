from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot_handlers.keyboards import main_menu_kb, phone_request_kb
from app.services.users import get_or_create_user_by_telegram_id

router = Router()


@router.message(CommandStart())
async def start(message: Message, session: AsyncSession):
    tg_user = message.from_user
    user = await get_or_create_user_by_telegram_id(
        session,
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )
    if user.phone:
        await message.answer(
            "👋 Добро пожаловать в Bententrade\n\n"
            "Вы уже зарегистрированы. Откройте приложение для каталога и заказов.",
            reply_markup=main_menu_kb(),
        )
        return
    await message.answer(
        "👋 Добро пожаловать в Bententrade\n\n"
        "Здесь мы коллективно набираем партии ротанга по оптовой цене. "
        "Когда партия набирает 100 кг — запускается производство.\n\n"
        "Для регистрации отправьте ваш номер телефона — затем все заказы оформляйте в приложении.",
        reply_markup=phone_request_kb(),
    )


@router.message(F.text == "Меню")
async def menu(message: Message):
    await message.answer("Выберите действие:", reply_markup=main_menu_kb())


@router.message(F.text == "📱 Каталог и заказы в приложении")
async def open_app_fallback(message: Message):
    await message.answer(
        "Откройте приложение по ссылке из меню бота или из описания.",
        reply_markup=main_menu_kb(),
    )


@router.message(F.text)
async def unknown_message(message: Message):
    await message.answer(
        "Используйте кнопки меню или нажмите /start.",
        reply_markup=main_menu_kb(),
    )

