from __future__ import annotations

from asyncio import Lock
from math import ceil, floor
from typing import final

from fastapi_sliding_window._backends.base import RateLimitBackend, RateLimitResult, _evict_if_needed


@final
class TokenBucketBackend(RateLimitBackend):
    def __init__(self, burst: int | None = None, max_keys: int = 10000) -> None:
        self._lock = Lock()
        self._data: dict[str, tuple[float, float]] = {}
        self._default_burst = burst
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
                reset_at=ceil(now + window),
                retry_after=window,
            )
        capacity = float(self._default_burst or limit)
        rate = limit / window if window > 0 else float("inf")
        reset_at = ceil(now + window)

        stored = self._data.get(key)
        if stored is None:
            tokens = capacity
        else:
            tokens, last_refill = stored
            tokens = min(capacity, tokens + (now - last_refill) * rate)

        if tokens >= cost:
            _evict_if_needed(self._data, self._max_keys, key)
            self._data[key] = (tokens - cost, now)
            return RateLimitResult(
                allowed=True,
                remaining=floor(tokens - cost),
                limit=limit,
                reset_at=reset_at,
            )

        retry_after = (cost - tokens) / rate
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
