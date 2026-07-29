from __future__ import annotations

import math
from asyncio import Lock

from fastapi_sliding_window._backends.base import RateLimitBackend, RateLimitResult, _evict_if_needed


class SlidingWindowCounterBackend(RateLimitBackend):
    def __init__(self, max_keys: int = 10000) -> None:
        self._prev: dict[str, tuple[float, int]] = {}
        self._curr: dict[str, tuple[float, int]] = {}
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

        prev_window_start = window_start - window
        prev_count = self._get_window_count(key, prev_window_start)
        curr_count = self._get_window_count(key, window_start)

        overlap_ratio = (window_start + window - now) / window
        weighted = prev_count * overlap_ratio + curr_count

        if weighted + cost <= limit:
            self._increment(key, window_start, cost)
            new_weighted = weighted + cost
            remaining = max(0, math.floor(limit - new_weighted))
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
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
            self._prev.pop(key, None)
            self._curr.pop(key, None)

    @staticmethod
    def _window_start(now: float, window: float) -> float:
        return now - (now % window)

    def _get_window_count(self, key: str, window_start: float) -> int:
        stored_start, count = self._curr.get(key, (0.0, 0))
        if stored_start == window_start:
            return count
        stored_start_prev, count_prev = self._prev.get(key, (0.0, 0))
        if stored_start_prev == window_start:
            return count_prev
        return 0

    def _increment(self, key: str, window_start: float, cost: int = 1) -> None:
        if key in self._curr:
            stored_start, count = self._curr[key]
            if stored_start == window_start:
                _evict_if_needed(self._curr, self._max_keys, key)
                self._curr[key] = (window_start, count + cost)
                return
            _evict_if_needed(self._prev, self._max_keys, key)
            _evict_if_needed(self._curr, self._max_keys, key)
            self._prev[key] = (stored_start, count)
        _evict_if_needed(self._curr, self._max_keys, key)
        self._curr[key] = (window_start, cost)
