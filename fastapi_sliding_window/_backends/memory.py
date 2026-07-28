from __future__ import annotations

from fastapi_sliding_window._algorithms.sliding_window_log import SlidingWindowLogBackend
from fastapi_sliding_window._backends.base import RateLimitBackend, RateLimitResult


class InMemoryBackend(RateLimitBackend):
    def __init__(self) -> None:
        self._backend = SlidingWindowLogBackend()

    async def check(self, key: str, limit: int, window: float, now: float) -> RateLimitResult:
        return await self._backend.check(key, limit, window, now)

    async def reset(self, key: str) -> None:
        await self._backend.reset(key)
