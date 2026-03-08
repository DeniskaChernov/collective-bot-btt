from __future__ import annotations

import hashlib
import hmac
import urllib.parse
from dataclasses import dataclass


@dataclass(frozen=True)
class TelegramWebAppUser:
    id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


def verify_init_data(init_data: str, *, bot_token: str) -> dict[str, str]:
    """
    Verifies Telegram WebApp initData per Telegram docs.
    Returns parsed key/value pairs if valid, raises ValueError otherwise.
    """
    parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise ValueError("Missing initData hash")

    data_check_string = "\n".join(f"{k}={parsed[k]}" for k in sorted(parsed.keys()))

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise ValueError("Invalid initData hash")

    return parsed

