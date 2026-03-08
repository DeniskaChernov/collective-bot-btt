"""Интеграционные тесты API: /public/me, /public/orders, admin PATCH order status."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Устанавливаем тестовое окружение до импорта app
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SCHEDULER_JOBSTORE_URL", "sqlite:///:memory:")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test:token")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD_HASH", "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.GY2YqYqYqYqYqY")  # любой валидный хеш

from app.main import app
from app.security.jwt import create_access_token


@pytest.mark.asyncio
async def test_public_me_requires_init_data() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.get("/public/me")
        assert r.status_code in (400, 422)


@pytest.mark.asyncio
async def test_public_orders_requires_init_data() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.get("/public/orders")
        assert r.status_code in (400, 422)


@pytest.mark.asyncio
async def test_admin_patch_order_status_requires_auth() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.patch(
            "/admin/orders/1/status",
            json={"status": "confirmed"},
        )
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_patch_order_status_with_token_returns_404_for_unknown_order() -> None:
    from app.config import get_settings

    settings = get_settings()
    token = create_access_token(settings, subject=settings.admin_username)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.patch(
            "/admin/orders/99999/status",
            json={"status": "confirmed"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404
