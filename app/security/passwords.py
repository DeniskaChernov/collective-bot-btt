from __future__ import annotations

import logging

import bcrypt

logger = logging.getLogger(__name__)

# bcrypt принимает пароль не длиннее 72 байт (UTF-8)
MAX_PASSWORD_BYTES = 72


def _truncate_password(password: str) -> bytes:
    data = password.encode("utf-8")
    if len(data) <= MAX_PASSWORD_BYTES:
        return data
    return data[:MAX_PASSWORD_BYTES]


def hash_password(password: str) -> str:
    pw = _truncate_password(password)
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash or not password_hash.strip():
        return False
    pw = _truncate_password(password)
    try:
        hash_bytes = password_hash.strip().encode("utf-8")
        return bcrypt.checkpw(pw, hash_bytes)
    except Exception as e:
        logger.warning("verify_password_failed: %s", e)
        return False
