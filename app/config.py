from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", case_sensitive=False)

    app_name: str = Field(default="collective-bot")
    environment: str = Field(default="production")
    log_level: str = Field(default="INFO")

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    database_url: str = Field(
        description="Async SQLAlchemy URL, e.g. postgresql+asyncpg://user:pass@host:5432/db"
    )
    database_pool_size: int = Field(default=5)
    database_max_overflow: int = Field(default=10)

    scheduler_jobstore_url: str = Field(
        description="Sync SQLAlchemy URL for APScheduler job store, e.g. postgresql+psycopg2://..."
    )
    scheduler_timezone: str = Field(default="UTC")

    telegram_bot_token: str = Field(repr=False)
    telegram_webhook_path: str = Field(
        description="Secret webhook path part, e.g. /telegram/webhook/<secret>"
    )
    telegram_secret_token: str | None = Field(
        default=None,
        repr=False,
        description="Optional X-Telegram-Bot-Api-Secret-Token header value",
    )
    webhook_base_url: str | None = Field(
        default=None,
        description="Optional base URL (https://...) to setTelegramWebhook on startup",
    )

    jwt_secret: str = Field(repr=False)
    jwt_issuer: str = Field(default="collective-admin")
    jwt_audience: str = Field(default="collective-admin")
    jwt_access_ttl_seconds: int = Field(default=3600)

    admin_username: str = Field(default="admin")
    admin_password_hash: str = Field(
        repr=False, description="Passlib hash, e.g. bcrypt"
    )

    admin_rate_limit_per_minute: int = Field(default=60)

    admin_telegram_chat_id: int | None = Field(
        default=None,
        description="Telegram chat id to receive admin notifications",
    )

    admin_telegram_user_id: int | None = Field(
        default=None,
        description="Telegram user id to receive admin DM notifications",
    )


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

