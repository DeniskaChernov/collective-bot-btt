"""
Скрипт запуска для Railway и других платформ.
Читает PORT из окружения и запускает uvicorn — так порт всегда передаётся корректно.
"""
from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
    )
