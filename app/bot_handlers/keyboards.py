from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from app.config import get_settings


def _mini_app_url() -> str | None:
    base = get_settings().webhook_base_url
    if not base:
        return None
    return base.rstrip("/") + "/mini-app/"


def phone_request_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Поделиться телефоном", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_kb() -> ReplyKeyboardMarkup:
    """Меню после регистрации: одна кнопка — открыть Mini App для каталога и заказов."""
    url = _mini_app_url()
    if url:
        keyboard = [[KeyboardButton(text="📱 Открыть приложение", web_app=WebAppInfo(url=url))]]
    else:
        keyboard = [[KeyboardButton(text="📱 Каталог и заказы в приложении")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def products_kb(products: list[tuple[int, str]]) -> "InlineKeyboardMarkup":
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    rows: list[list[InlineKeyboardButton]] = []
    for product_id, title in products:
        rows.append(
            [InlineKeyboardButton(text=title, callback_data=f"product:{product_id}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inline_open_app_kb() -> "InlineKeyboardMarkup":
    """Инлайн-кнопка «Открыть приложение» для использования в edit_text."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    url = _mini_app_url()
    if not url:
        return InlineKeyboardMarkup(inline_keyboard=[])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📱 Открыть приложение", web_app=WebAppInfo(url=url))]
        ]
    )


def product_actions_kb(product_id: int) -> "InlineKeyboardMarkup":
    """Не используется: заказы только в Mini App. Оставлено для совместимости."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    url = _mini_app_url()
    if url:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📱 Открыть приложение для заказа", web_app=WebAppInfo(url=url))]
            ]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Откройте приложение по ссылке в меню", callback_data="back:catalog")]
        ]
    )


