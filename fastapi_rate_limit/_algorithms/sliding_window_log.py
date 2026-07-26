from __future__ import annotations

import math
from collections import defaultdict, deque

from fastapi_rate_limit._backends.base import RateLimitBackend, RateLimitResult


class SlidingWindowLogBackend(RateLimitBackend):
    def __init__(self) -> None:
        self._data: dict[str, deque[float]] = defaultdict(deque)

    async def check(self, key: str, limit: int, window: float, now: float) -> RateLimitResult:
        timestamps = self._data[key]
        window_start = now - window

        while timestamps and timestamps[0] <= window_start:
            timestamps.popleft()

        reset_at = math.ceil(now + window)

        if len(timestamps) < limit:
            timestamps.append(now)
            return RateLimitResult(
                allowed=True,
                remaining=limit - len(timestamps),
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
        self._data.pop(key, None)
