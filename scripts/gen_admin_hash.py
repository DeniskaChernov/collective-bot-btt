#!/usr/bin/env python3
"""
Скрипт для генерации хеша пароля админа.
Запусти: python scripts/gen_admin_hash.py
Скопируй вывод в переменную ADMIN_PASSWORD_HASH в Railway.
Входи в админку логином из ADMIN_USERNAME и паролем, который ввёл ниже.
"""
from __future__ import annotations

import getpass
import sys

try:
    from passlib.hash import bcrypt
except ImportError:
    print("Установи passlib: pip install passlib[bcrypt]", file=sys.stderr)
    sys.exit(1)

def main() -> None:
    password = getpass.getpass("Введи пароль для админа (будет скрыт): ")
    if not password:
        print("Пароль не задан.", file=sys.stderr)
        sys.exit(1)
    if len(password.encode("utf-8")) > 72:
        print("Пароль не длиннее 72 байт (bcrypt).", file=sys.stderr)
        sys.exit(1)
    h = bcrypt.hash(password)
    print()
    print("Скопируй строку ниже в ADMIN_PASSWORD_HASH в Railway:")
    print()
    print(h)
    print()
    print("Логин в админке: значение ADMIN_USERNAME (часто admin)")
    print("Пароль в админке: тот, что ты только что ввёл")

if __name__ == "__main__":
    main()
