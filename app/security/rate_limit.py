from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import Request

from app.config import Settings
from app.errors import Forbidden


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class FixedWindowRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, Deque[float]] = defaultdict(deque)

    def check(self, *, key: str, limit: int, window_seconds: int) -> None:
        now = time.time()
        q = self._hits[key]
        cutoff = now - window_seconds
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= limit:
            raise Forbidden("Rate limit exceeded")
        q.append(now)


async def admin_rate_limit(request: Request) -> None:
    settings: Settings = request.app.state.settings
    limiter: FixedWindowRateLimiter = request.app.state.admin_rate_limiter
    limiter.check(
        key=_client_key(request),
        limit=settings.admin_rate_limit_per_minute,
        window_seconds=60,
    )

