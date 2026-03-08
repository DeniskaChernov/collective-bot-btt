from __future__ import annotations

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# bcrypt принимает пароль не длиннее 72 байт (UTF-8)
MAX_PASSWORD_BYTES = 72


def _truncate_password(password: str) -> str:
    data = password.encode("utf-8")
    if len(data) <= MAX_PASSWORD_BYTES:
        return password
    return data[:MAX_PASSWORD_BYTES].decode("utf-8", errors="ignore") or ""


def hash_password(password: str) -> str:
    return _pwd_context.hash(_truncate_password(password))


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(_truncate_password(password), password_hash)

