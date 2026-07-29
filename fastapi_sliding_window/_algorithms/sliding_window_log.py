from __future__ import annotations

import math
from asyncio import Lock
from collections import defaultdict, deque

from fastapi_sliding_window._backends.base import RateLimitBackend, RateLimitResult, _evict_if_needed


class SlidingWindowLogBackend(RateLimitBackend):
    def __init__(self, max_keys: int = 10000) -> None:
        self._data: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()
        self._max_keys = max_keys

    async def check(self, key: str, limit: int, window: float, now: float, cost: int = 1) -> RateLimitResult:
        async with self._lock:
            return self._check_locked(key, limit, window, now, cost)

    def _check_locked(self, key: str, limit: int, window: float, now: float, cost: int) -> RateLimitResult:
        if limit <= 0:
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=limit,
                reset_at=math.ceil(now + window),
                retry_after=window,
            )
        timestamps = self._data[key]
        window_start = now - window

        while timestamps and timestamps[0] <= window_start:
            timestamps.popleft()

        reset_at = math.ceil(now + window)

        if len(timestamps) + cost <= limit:
            _evict_if_needed(self._data, self._max_keys, key)
            for _ in range(cost):
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
        async with self._lock:
            self._data.pop(key, None)
