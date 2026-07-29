from __future__ import annotations

from asyncio import Lock
from math import ceil, floor
from typing import final

from fastapi_sliding_window._backends.base import RateLimitBackend, RateLimitResult, _evict_if_needed


@final
class GCRABackend(RateLimitBackend):
    def __init__(self, burst: int | None = None, max_keys: int = 10000) -> None:
        self._lock = Lock()
        self._data: dict[str, float] = {}
        self._default_burst = burst
        self._max_keys = max_keys

    async def check(self, key: str, limit: int, window: float, now: float, cost: int = 1) -> RateLimitResult:
        if limit == 0:
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=0,
                reset_at=now + window,
                retry_after=window,
            )
        async with self._lock:
            return self._check_locked(key, limit, window, now, cost)

    def _check_locked(self, key: str, limit: int, window: float, now: float, cost: int) -> RateLimitResult:
        T = window / limit if limit > 0 else 1.0
        burst = self._default_burst or limit
        tau = (burst - 1) * T
        reset_at = ceil(now + window)

        tat = self._data.get(key, 0.0)

        if tat <= now:
            _evict_if_needed(self._data, self._max_keys, key)
            new_tat = now + cost * T
            self._data[key] = new_tat
            remaining = max(0, burst - cost)
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                limit=limit,
                reset_at=reset_at,
            )

        delay = tat - now
        if delay <= tau:
            _evict_if_needed(self._data, self._max_keys, key)
            new_tat = tat + cost * T
            self._data[key] = new_tat
            remaining = max(0, floor((tau - delay) / T))
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                limit=limit,
                reset_at=reset_at,
            )

        retry_after = delay - tau
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
