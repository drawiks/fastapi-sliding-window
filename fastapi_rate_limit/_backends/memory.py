from __future__ import annotations

import asyncio
import math
from collections import defaultdict, deque

from fastapi_rate_limit._backends.base import RateLimitBackend, RateLimitResult


class InMemoryBackend(RateLimitBackend):
    def __init__(self) -> None:
        self._data: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str, limit: int, window: float, now: float) -> RateLimitResult:
        async with self._lock:
            return self._check_locked(key, limit, window, now)

    def _check_locked(self, key: str, limit: int, window: float, now: float) -> RateLimitResult:
        timestamps = self._data[key]
        window_start = now - window

        while timestamps and timestamps[0] <= window_start:
            timestamps.popleft()

        remaining = max(0, limit - len(timestamps))
        reset_at = math.ceil(now + window)

        if len(timestamps) < limit:
            timestamps.append(now)
            return RateLimitResult(
                allowed=True,
                remaining=remaining - 1,
                limit=limit,
                reset_at=reset_at,
            )

        oldest = timestamps[0]
        retry_after = oldest + window - now
        return RateLimitResult(
            allowed=False,
            remaining=0,
            limit=limit,
            reset_at=reset_at,
            retry_after=max(0.0, retry_after),
        )

    async def reset(self, key: str) -> None:
        async with self._lock:
            self._data.pop(key, None)
