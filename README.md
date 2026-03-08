# Bententrade — коллективные заказы (Telegram Bot + Mini App)

Сервис для коллективного набора партий товара (ротанг): пользователи добавляют вес в корзину (шаг 5 кг), при достижении порога (например 100 кг) запускается 24-часовой добор, затем партия закрывается. Регистрация — в боте (телефон), все заказы оформляются в Telegram Mini App.

**Стек:** Python 3.12, FastAPI, SQLAlchemy (async), aiogram 3, APScheduler, Alembic.

---

## Быстрый старт

1. Клонируйте репозиторий и установите зависимости:

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

2. Скопируйте пример переменных окружения и заполните значения:

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/macOS
```

3. Поднимите БД и примените миграции:

```bash
alembic upgrade head
```

4. Запустите приложение:

```bash
uvicorn app.main:app --reload
```

---

## Переменные окружения

Описание переменных — в файле [.env.example](.env.example). Основные:

| Переменная | Описание |
|------------|----------|
| `DATABASE_URL` | PostgreSQL (async): `postgresql+asyncpg://user:pass@host:5432/db` |
| `SCHEDULER_JOBSTORE_URL` | Тот же PostgreSQL (sync): `postgresql+psycopg2://...` |
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `TELEGRAM_WEBHOOK_PATH` | Секретный путь webhook: `/telegram/webhook/<secret>` |
| `WEBHOOK_BASE_URL` | Публичный URL сервера (для setWebhook и Mini App) |
| `JWT_SECRET` | Секрет для JWT админки |
| `ADMIN_USERNAME` | Логин админа |
| `ADMIN_PASSWORD_HASH` | Хеш пароля (bcrypt): `python -c "import passlib.hash; print(passlib.hash.bcrypt.hash('пароль'))"` |

---

## Архитектура

```
┌─────────────────┐     webhook      ┌──────────────────┐
│  Telegram Bot   │ ◄───────────────► │  FastAPI (API)   │
│  (регистрация,  │                   │  /public/*       │
│   кнопка в      │                   │  /admin/*        │
│   Mini App)     │                   │  /telegram/      │
└────────┬────────┘                   └────────┬─────────┘
         │                                      │
         │  открывает по ссылке                 │  initData
         ▼                                      ▼
┌─────────────────┐                   ┌──────────────────┐
│  Telegram       │ ─── X-Telegram-  │  PostgreSQL +    │
│  Mini App       │     Init-Data ──► │  APScheduler     │
│  (каталог,      │                   │  (партии, таймер │
│   корзина,      │                   │   24ч)           │
│   заказы)       │                   └──────────────────┘
└─────────────────┘
```

- **Бот:** `/start` → запрос контакта (телефон) → кнопка «Открыть приложение». Все заказы только в Mini App.
- **Mini App:** каталог, корзина (±5 кг), оформление заказа (самовывоз / доставка / Uzum Market), вкладка «Мои заказы». Работает только из Telegram (передаётся `initData`).
- **API:** публичные эндпоинты (`/public/products`, `/public/cart`, `/public/orders`, `/public/me`, `/public/orders`), админка (`/admin/auth/login`, `/admin/orders`, `/admin/products`, `/admin/users`), webhook для бота (`/telegram/webhook/...`).

---

## Миграции (Alembic)

Первичное создание таблиц (если ещё не применяли миграции):

```bash
alembic upgrade head
```

Для разработки при изменении моделей:

```bash
alembic revision --autogenerate -m "описание"
alembic upgrade head
```

На проде перед запуском приложения всегда выполняйте `alembic upgrade head`.

---

## Админка

- **REST API:** логин `POST /admin/auth/login`, заказы `GET/PATCH /admin/orders`, товары и пользователи — см. OpenAPI `/docs`.
- **Веб-интерфейс:** после запуска приложения откройте в браузере:

  ```
  https://<ваш-домен>/admin-ui/
  ```

  Логин и пароль — из `ADMIN_USERNAME` и пароля, чей хеш указан в `ADMIN_PASSWORD_HASH`.

---

## Деплой (Docker + Railway)

В проекте есть `Dockerfile` и `railway.json`.

1. Соберите образ: `docker build -t collective-app .`
2. Запуск: контейнер ожидает переменную `PORT`; старт через `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
3. В Railway задайте переменные окружения из `.env.example` и выполните миграции при деплое (job или команда в настройках).

Локально с Docker:

```bash
docker build -t collective-app .
docker run -p 8000:8000 -e PORT=8000 --env-file .env collective-app
```

---

## Тесты

```bash
# Все тесты (используется in-memory SQLite, env задаётся автоматически в test_api)
pytest tests -v

# Только юнит-тесты (корзина, заказы, пользователи, схемы)
pytest tests/test_cart_and_orders.py tests/test_users.py tests/test_schemas.py -v
```

Для интеграционных тестов API (`tests/test_api.py`) задаётся `TESTING=1` и `DATABASE_URL=sqlite+aiosqlite:///:memory:` — таблицы создаются в lifespan.

---

## CI/CD

В репозитории настроен GitHub Actions (`.github/workflows/ci.yml`):

- **Lint:** Ruff (проверка кода).
- **Test:** `pytest tests -v` с тестовой БД.

При пуше в `main`/`master` и при pull request запускаются оба шага.

---

## Полезные ссылки

- **Mini App (пользователи):** `https://<WEBHOOK_BASE_URL>/mini-app/`
- **Админ-интерфейс:** `https://<WEBHOOK_BASE_URL>/admin-ui/`
- **OpenAPI:** `https://<ваш-домен>/docs`
