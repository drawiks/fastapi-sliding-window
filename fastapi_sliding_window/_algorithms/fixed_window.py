from __future__ import annotations

import math
from asyncio import Lock

from fastapi_sliding_window._backends.base import RateLimitBackend, RateLimitResult, _evict_if_needed


class FixedWindowBackend(RateLimitBackend):
    def __init__(self, max_keys: int = 10000) -> None:
        self._data: dict[str, tuple[float, int]] = {}
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
        window_start = self._window_start(now, window)
        reset_at = math.ceil(window_start + window)

        stored_start, count = self._data.get(key, (0.0, 0))

        if stored_start != window_start:
            _evict_if_needed(self._data, self._max_keys, key)
            self._data[key] = (window_start, cost)
            new_count = cost
            return RateLimitResult(
                allowed=True,
                remaining=max(0, limit - new_count),
                limit=limit,
                reset_at=reset_at,
            )

        if count + cost <= limit:
            _evict_if_needed(self._data, self._max_keys, key)
            self._data[key] = (window_start, count + cost)
            return RateLimitResult(
                allowed=True,
                remaining=limit - count - cost,
                limit=limit,
                reset_at=reset_at,
            )

        retry_after = (window_start + window) - now
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

    @staticmethod
    def _window_start(now: float, window: float) -> float:
        return now - (now % window)
