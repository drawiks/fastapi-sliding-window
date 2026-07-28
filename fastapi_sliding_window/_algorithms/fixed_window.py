from __future__ import annotations

from asyncio import Lock
import math

from fastapi_sliding_window._backends.base import RateLimitBackend, RateLimitResult


class FixedWindowBackend(RateLimitBackend):
    def __init__(self) -> None:
        self._data: dict[str, tuple[float, int]] = {}
        self._lock = Lock()

    async def check(self, key: str, limit: int, window: float, now: float) -> RateLimitResult:
        async with self._lock:
            return self._check_locked(key, limit, window, now)

    def _check_locked(self, key: str, limit: int, window: float, now: float) -> RateLimitResult:
        window_start = self._window_start(now, window)
        reset_at = math.ceil(window_start + window)

        stored_start, count = self._data.get(key, (0.0, 0))

        if stored_start != window_start:
            self._data[key] = (window_start, 1)
            return RateLimitResult(
                allowed=True,
                remaining=limit - 1,
                limit=limit,
                reset_at=reset_at,
            )

        if count < limit:
            self._data[key] = (window_start, count + 1)
            return RateLimitResult(
                allowed=True,
                remaining=limit - count - 1,
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
