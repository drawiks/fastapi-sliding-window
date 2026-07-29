from __future__ import annotations

import asyncio
from time import time
from typing import Any, cast
from unittest.mock import AsyncMock

from fastapi_sliding_window._backends.base import RateLimitResult
from fastapi_sliding_window._backends.fallback import (
    CircuitState,
    RedisWithFallbackBackend,
)
from fastapi_sliding_window._backends.memory import InMemoryBackend


class FakeRedisBackend:
    def __init__(self) -> None:
        self._check = AsyncMock()
        self._reset = AsyncMock()

    async def check(self, key: str, limit: int, window: float, now: float, cost: int = 1) -> RateLimitResult:
        return await self._check(key, limit, window, now, cost=cost)

    async def reset(self, key: str) -> None:
        await self._reset(key)


async def test_fallback_uses_redis_when_healthy() -> None:
    redis = FakeRedisBackend()
    fallback = InMemoryBackend()
    backend = RedisWithFallbackBackend.__new__(RedisWithFallbackBackend)
    backend._redis = cast(Any, redis)
    backend._fallback = fallback
    backend._circuit = CircuitState()
    backend._threshold = 5
    backend._recovery = 30.0
    backend._lock = asyncio.Lock()

    expected = RateLimitResult(allowed=True, remaining=9, limit=10, reset_at=100.0)
    redis._check = AsyncMock(return_value=expected)

    result = await backend.check("k", 10, 60.0, 0.0, cost=1)
    assert result == expected
    assert backend._circuit.failures == 0
    assert backend._circuit.state == "closed"


async def test_fallback_falls_back_on_redis_error() -> None:
    redis = FakeRedisBackend()
    fallback = InMemoryBackend()
    backend = RedisWithFallbackBackend.__new__(RedisWithFallbackBackend)
    backend._redis = cast(Any, redis)
    backend._fallback = fallback
    backend._circuit = CircuitState()
    backend._threshold = 5
    backend._recovery = 30.0
    backend._lock = asyncio.Lock()

    redis._check = AsyncMock(side_effect=ConnectionError("redis down"))

    result = await backend.check("k", 10, 60.0, 0.0, cost=1)
    assert result.allowed
    assert backend._circuit.failures == 1
    assert backend._circuit.state == "closed"


async def test_fallback_opens_circuit_after_threshold() -> None:
    redis = FakeRedisBackend()
    fallback = InMemoryBackend()
    backend = RedisWithFallbackBackend.__new__(RedisWithFallbackBackend)
    backend._redis = cast(Any, redis)
    backend._fallback = fallback
    backend._circuit = CircuitState()
    backend._threshold = 3
    backend._recovery = 30.0
    backend._lock = asyncio.Lock()

    redis._check = AsyncMock(side_effect=ConnectionError("redis down"))

    for _ in range(3):
        result = await backend.check("k", 10, 60.0, 0.0, cost=1)
        assert result.allowed

    assert backend._circuit.state == "open"
    assert backend._circuit.last_open > 0


async def test_fallback_uses_fallback_when_circuit_open() -> None:
    redis = FakeRedisBackend()
    fallback = InMemoryBackend()
    backend = RedisWithFallbackBackend.__new__(RedisWithFallbackBackend)
    backend._redis = cast(Any, redis)
    backend._fallback = fallback
    backend._circuit = CircuitState(failures=5, state="open", last_open=time())
    backend._threshold = 5
    backend._recovery = 30.0
    backend._lock = asyncio.Lock()

    result = await backend.check("k", 10, 60.0, 0.0, cost=1)
    assert result.allowed
    redis._check.assert_not_called()


async def test_fallback_transitions_to_half_open_after_recovery() -> None:
    redis = FakeRedisBackend()
    fallback = InMemoryBackend()
    backend = RedisWithFallbackBackend.__new__(RedisWithFallbackBackend)
    backend._redis = cast(Any, redis)
    backend._fallback = fallback
    backend._circuit = CircuitState(failures=5, state="open", last_open=0.0)
    backend._threshold = 5
    backend._recovery = 0.0
    backend._lock = asyncio.Lock()

    expected = RateLimitResult(allowed=True, remaining=9, limit=10, reset_at=100.0)
    redis._check = AsyncMock(return_value=expected)

    result = await backend.check("k", 10, 60.0, 0.0, cost=1)
    assert result == expected
    assert backend._circuit.state == "closed"


async def test_fallback_handles_reset_with_redis_error() -> None:
    redis = FakeRedisBackend()
    fallback = InMemoryBackend()
    backend = RedisWithFallbackBackend.__new__(RedisWithFallbackBackend)
    backend._redis = cast(Any, redis)
    backend._fallback = fallback
    backend._circuit = CircuitState()
    backend._threshold = 5
    backend._recovery = 30.0
    backend._lock = asyncio.Lock()

    redis._reset = AsyncMock(side_effect=TimeoutError("timeout"))

    await fallback.check("k", 10, 60.0, 0.0, cost=1)
    await backend.reset("k")
    result = await backend.check("k", 10, 60.0, 0.0, cost=1)
    assert result.allowed


async def test_fallback_concurrent_circuit_breaker() -> None:
    redis = FakeRedisBackend()
    fallback = InMemoryBackend()
    backend = RedisWithFallbackBackend.__new__(RedisWithFallbackBackend)
    backend._redis = cast(Any, redis)
    backend._fallback = fallback
    backend._circuit = CircuitState()
    backend._threshold = 3
    backend._recovery = 30.0
    backend._lock = asyncio.Lock()

    redis._check = AsyncMock(side_effect=ConnectionError("redis down"))

    results = await asyncio.gather(*[backend.check("k", 10, 60.0, 0.0) for _ in range(10)])
    assert all(r.allowed for r in results)
    assert backend._circuit.state == "open"
