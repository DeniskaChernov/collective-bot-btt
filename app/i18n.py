from __future__ import annotations

from typing import Any

SUPPORTED_LANGS = {"ru", "uz"}
DEFAULT_LANG = "ru"

TEXTS: dict[str, dict[str, str]] = {
    "choose_language": {
        "ru": "Выберите язык / Tilni tanlang:",
        "uz": "Tilni tanlang / Выберите язык:",
    },
    "language_changed": {
        "ru": "Язык изменён на русский.",
        "uz": "Til o'zbek tiliga o'zgartirildi.",
    },
    "language_saved_need_phone": {
        "ru": "Язык сохранён.\n\nДля регистрации отправьте номер телефона.",
        "uz": "Til saqlandi.\n\nRo'yxatdan o'tish uchun telefon raqamingizni yuboring.",
    },
    "welcome_registered": {
        "ru": "👋 Добро пожаловать в Bententrade\n\nВы уже зарегистрированы. Откройте приложение для каталога и заказов.",
        "uz": "👋 Bententrade'ga xush kelibsiz\n\nSiz allaqachon ro'yxatdan o'tgansiz. Katalog va buyurtmalar uchun ilovani oching.",
    },
    "welcome_need_phone": {
        "ru": "👋 Добро пожаловать в Bententrade\n\nЗдесь мы коллективно набираем партии ротанга по оптовой цене. Когда партия набирает 100 кг — запускается производство.\n\nДля регистрации отправьте ваш номер телефона — затем все заказы оформляйте в приложении.",
        "uz": "👋 Bententrade'ga xush kelibsiz\n\nBu yerda biz rattan partiyalarini ulgurji narxda birgalikda yig'amiz. Partiya 100 kg ga yetganda ishlab chiqarish boshlanadi.\n\nRo'yxatdan o'tish uchun telefon raqamingizni yuboring, keyin barcha buyurtmalarni ilovada rasmiylashtirasiz.",
    },
    "registration_done": {
        "ru": "✅ Регистрация завершена\n\nТеперь откройте приложение — там каталог, корзина и оформление заказов.",
        "uz": "✅ Ro'yxatdan o'tish yakunlandi\n\nEndi ilovani oching — u yerda katalog, savat va buyurtma rasmiylashtirish mavjud.",
    },
    "menu_choose_action": {
        "ru": "Выберите действие:",
        "uz": "Kerakli bo'limni tanlang:",
    },
    "open_app_fallback": {
        "ru": "Откройте приложение по кнопке в меню бота.",
        "uz": "Ilovani bot menyusidagi tugma orqali oching.",
    },
    "unknown_message": {
        "ru": "Используйте кнопки меню или нажмите /start.",
        "uz": "Menyu tugmalaridan foydalaning yoki /start ni bosing.",
    },
    "share_phone": {
        "ru": "Поделиться телефоном",
        "uz": "Telefon raqamni yuborish",
    },
    "open_app": {
        "ru": "📱 Открыть приложение",
        "uz": "📱 Ilovani ochish",
    },
    "change_language": {
        "ru": "🌐 Сменить язык",
        "uz": "🌐 Tilni o'zgartirish",
    },
    "order_created": {
        "ru": "✅ Заказ создан: товар #{product_id}, {weight_total} кг.\nМы уведомим вас о запуске и закрытии партии.",
        "uz": "✅ Buyurtma yaratildi: mahsulot #{product_id}, {weight_total} kg.\nPartiya ishga tushishi va yopilishi haqida sizga xabar beramiz.",
    },
    "threshold_reached": {
        "ru": "🎉 Партия достигла 100 кг!\nЗапущен добор 24 часа. Вы можете увеличить заказ до закрытия партии.",
        "uz": "🎉 Partiya 100 kg ga yetdi!\n24 soatlik qo'shimcha yig'im boshlandi. Partiya yopilguncha buyurtmangizni oshirishingiz mumkin.",
    },
    "batch_closed": {
        "ru": "🚀 Партия закрыта.\nПроизводство запущено. Ожидайте уведомление о готовности.",
        "uz": "🚀 Partiya yopildi.\nIshlab chiqarish boshlandi. Tayyor bo'lganda sizga xabar beramiz.",
    },
    "order_confirmed": {
        "ru": "✅ Заказ #{order_id} подтверждён.",
        "uz": "✅ Buyurtma #{order_id} tasdiqlandi.",
    },
    "order_cancelled": {
        "ru": "❌ Заказ #{order_id} отменён.",
        "uz": "❌ Buyurtma #{order_id} bekor qilindi.",
    },
    "order_status_changed": {
        "ru": "📦 Заказ #{order_id}: статус изменён на «{status_text}».",
        "uz": "📦 Buyurtma #{order_id}: holati «{status_text}» ga o'zgartirildi.",
    },
    "order_received": {
        "ru": "📦 Заказ #{order_id} отмечен как полученный.",
        "uz": "📦 Buyurtma #{order_id} olingan deb belgilandi.",
    },
}

ORDER_STATUS_TEXTS: dict[str, dict[str, str]] = {
    "pending": {"ru": "ожидает", "uz": "kutilmoqda"},
    "confirmed": {"ru": "подтверждён", "uz": "tasdiqlangan"},
    "cancelled": {"ru": "отменён", "uz": "bekor qilingan"},
    "completed": {"ru": "выполнен", "uz": "yakunlangan"},
    "received": {"ru": "получен", "uz": "olingan"},
}


def normalize_lang(value: str | None) -> str:
    if not value:
        return DEFAULT_LANG
    value = value.strip().lower()
    return value if value in SUPPORTED_LANGS else DEFAULT_LANG


def t(key: str, lang: str | None = None, **kwargs: Any) -> str:
    current_lang = normalize_lang(lang)
    template = TEXTS.get(key, {}).get(current_lang) or TEXTS.get(key, {}).get(DEFAULT_LANG) or key
    return template.format(**kwargs)


def order_status_text(status: str, lang: str | None = None) -> str:
    current_lang = normalize_lang(lang)
    return ORDER_STATUS_TEXTS.get(status, {}).get(current_lang) or ORDER_STATUS_TEXTS.get(status, {}).get(DEFAULT_LANG) or status
