from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Загружаем .env из корня проекта (рядом с alembic.ini) или из текущей папки
_root = Path(__file__).resolve().parent.parent
load_dotenv(_root / ".env")
load_dotenv(Path.cwd() / ".env")

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _sync_url_from_env() -> str:
    url = os.environ.get("ALEMBIC_DATABASE_URL") or os.environ.get("SCHEDULER_JOBSTORE_URL") or os.environ.get(
        "DATABASE_URL", ""
    )
    if not url:
        raise RuntimeError(
            "Не задан URL базы. Скопируйте .env.example в .env и укажите DATABASE_URL "
            "(например: postgresql+asyncpg://user:password@localhost:5432/collective)"
        )
    return (
        url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        .replace("postgres://", "postgresql://")
    )


def run_migrations_offline() -> None:
    context.configure(
        url=_sync_url_from_env(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _sync_url_from_env()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

