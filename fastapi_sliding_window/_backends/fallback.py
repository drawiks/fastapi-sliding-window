from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import monotonic
from typing import Literal

from fastapi_sliding_window._backends.base import RateLimitBackend, RateLimitResult
from fastapi_sliding_window._backends.memory import InMemoryBackend
from fastapi_sliding_window._backends.redis import RedisBackend
from fastapi_sliding_window._types import Algorithm

try:
    from redis.exceptions import ConnectionError as RedisConnectionError
    from redis.exceptions import TimeoutError as RedisTimeoutError
except ImportError:
    RedisConnectionError = ConnectionError  # type: ignore[assignment, misc]
    RedisTimeoutError = TimeoutError  # type: ignore[assignment, misc]


@dataclass
class CircuitState:
    failures: int = 0
    state: Literal["closed", "open", "half-open"] = "closed"
    last_open: float = 0.0


class RedisWithFallbackBackend(RateLimitBackend):
    def __init__(
        self,
        redis_url: str,
        algorithm: str = "sliding_window_log",
        key_prefix: str = "rl:",
        burst: int | None = None,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        fallback: RateLimitBackend | None = None,
    ) -> None:
        self._redis = RedisBackend(redis_url, algorithm, key_prefix, burst)
        alg = Algorithm(algorithm) if isinstance(algorithm, str) else algorithm
        self._fallback = fallback or InMemoryBackend(algorithm=alg, burst=burst)
        self._circuit = CircuitState()
        self._threshold = failure_threshold
        self._recovery = recovery_timeout
        self._lock = asyncio.Lock()

    async def check(self, key: str, limit: int, window: float, now: float, cost: int = 1) -> RateLimitResult:
        async with self._lock:
            return await self._check_locked(key, limit, window, now, cost)

    async def _check_locked(self, key: str, limit: int, window: float, now: float, cost: int) -> RateLimitResult:
        if self._circuit.state == "open":
            if monotonic() - self._circuit.last_open >= self._recovery:
                self._circuit.state = "half-open"
                self._circuit.failures = 0
            else:
                return await self._fallback.check(key, limit, window, now, cost=cost)
        try:
            result = await self._redis.check(key, limit, window, now, cost=cost)
            self._circuit.failures = 0
            self._circuit.state = "closed"
            self._circuit.last_open = 0.0
            return result
        except (
            ConnectionError,
            TimeoutError,
            OSError,
            RedisConnectionError,
            RedisTimeoutError,
        ):
            self._circuit.failures += 1
            if self._circuit.failures >= self._threshold:
                self._circuit.state = "open"
                self._circuit.last_open = monotonic()
            return await self._fallback.check(key, limit, window, now, cost=cost)

    async def reset(self, key: str) -> None:
        try:
            await self._redis.reset(key)
        except (
            ConnectionError,
            TimeoutError,
            OSError,
            RedisConnectionError,
            RedisTimeoutError,
        ):
            await self._fallback.reset(key)
