from __future__ import annotations

import math

from fastapi_sliding_window._backends.base import RateLimitBackend, RateLimitResult


class SlidingWindowCounterBackend(RateLimitBackend):
    def __init__(self) -> None:
        self._prev: dict[str, tuple[float, int]] = {}
        self._curr: dict[str, tuple[float, int]] = {}

    async def check(self, key: str, limit: int, window: float, now: float) -> RateLimitResult:
        window_start = self._window_start(now, window)
        reset_at = math.ceil(window_start + window)

        prev_window_start = window_start - window
        prev_count = self._get_window_count(key, prev_window_start)
        curr_count = self._get_window_count(key, window_start)

        overlap_ratio = (window_start + window - now) / window
        weighted = prev_count * overlap_ratio + curr_count

        if weighted < limit:
            self._increment(key, window_start)
            new_weighted = prev_count * overlap_ratio + curr_count + 1
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

    def _increment(self, key: str, window_start: float) -> None:
        stored_start, count = self._curr.get(key, (0.0, 0))
        if stored_start == window_start:
            self._curr[key] = (window_start, count + 1)
        else:
            self._prev[key] = self._curr.get(key, (0.0, 0))
            self._curr[key] = (window_start, 1)
