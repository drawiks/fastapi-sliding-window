from __future__ import annotations

from fastapi_sliding_window._backends.base import RateLimitBackend, RateLimitResult
from fastapi_sliding_window._types import Algorithm
from fastapi_sliding_window._utils import make_backend


class InMemoryBackend(RateLimitBackend):
    def __init__(
        self,
        algorithm: Algorithm = Algorithm.SLIDING_WINDOW_LOG,
        burst: int | None = None,
    ) -> None:
        self._backend = make_backend(algorithm, burst=burst)

    async def check(self, key: str, limit: int, window: float, now: float, cost: int = 1) -> RateLimitResult:
        return await self._backend.check(key, limit, window, now, cost=cost)

    async def reset(self, key: str) -> None:
        await self._backend.reset(key)
