from __future__ import annotations

from math import ceil

import pytest

from fastapi_sliding_window._backends.redis import RedisBackend
from fastapi_sliding_window._utils import from_url


def redis_available() -> bool:
    try:
        import redis.asyncio  # noqa: F401
    except ImportError:
        return False
    try:
        import socket

        s = socket.create_connection(("localhost", 6379), timeout=1.0)
        s.close()
        return True
    except (OSError, ConnectionError):
        return False


@pytest.fixture
async def redis_backend():
    backend = RedisBackend("redis://localhost:6379/0", algorithm="sliding_window_log")
    await backend.reset("key")
    yield backend
    await backend.reset("key")
    await backend._ensure_redis()
    await backend._redis.flushdb()  # type: ignore[union-attr]


@pytest.mark.skipif(not redis_available(), reason="Redis not available")
@pytest.mark.asyncio
async def test_redis_allows_within_limit(redis_backend: RedisBackend) -> None:
    result = await redis_backend.check("key", limit=3, window=10.0, now=100.0)
    assert result.allowed is True
    assert result.remaining == 2


@pytest.mark.skipif(not redis_available(), reason="Redis not available")
@pytest.mark.asyncio
async def test_redis_blocks_after_limit(redis_backend: RedisBackend) -> None:
    for _ in range(3):
        result = await redis_backend.check("key", limit=3, window=10.0, now=100.0)
        assert result.allowed is True
    result = await redis_backend.check("key", limit=3, window=10.0, now=100.0)
    assert result.allowed is False
    assert result.remaining == 0


@pytest.mark.skipif(not redis_available(), reason="Redis not available")
@pytest.mark.asyncio
async def test_redis_window_expiry(redis_backend: RedisBackend) -> None:
    for _ in range(3):
        await redis_backend.check("key", limit=3, window=5.0, now=100.0)
    result = await redis_backend.check("key", limit=3, window=5.0, now=105.1)
    assert result.allowed is True


@pytest.mark.skipif(not redis_available(), reason="Redis not available")
@pytest.mark.asyncio
async def test_redis_reset(redis_backend: RedisBackend) -> None:
    for _ in range(3):
        await redis_backend.check("key", limit=3, window=10.0, now=100.0)
    await redis_backend.reset("key")
    result = await redis_backend.check("key", limit=3, window=10.0, now=100.1)
    assert result.allowed is True
    assert result.remaining == 2


@pytest.mark.skipif(not redis_available(), reason="Redis not available")
@pytest.mark.asyncio
async def test_redis_different_keys(redis_backend: RedisBackend) -> None:
    for _ in range(3):
        await redis_backend.check("a", limit=3, window=10.0, now=100.0)
    result_a = await redis_backend.check("a", limit=3, window=10.0, now=100.0)
    assert result_a.allowed is False
    result_b = await redis_backend.check("b", limit=3, window=10.0, now=100.0)
    assert result_b.allowed is True


@pytest.mark.skipif(not redis_available(), reason="Redis not available")
@pytest.mark.asyncio
async def test_redis_reset_at(redis_backend: RedisBackend) -> None:
    result = await redis_backend.check("key", limit=5, window=60.0, now=100.0)
    assert result.reset_at == ceil(100 + 60)


@pytest.mark.skipif(not redis_available(), reason="Redis not available")
@pytest.mark.asyncio
async def test_redis_fixed_window(redis_backend: RedisBackend) -> None:
    backend = RedisBackend("redis://localhost:6379/0", algorithm="fixed_window")
    await backend.reset("key")
    result = await backend.check("key", limit=3, window=10.0, now=100.0)
    assert result.allowed is True
    for _ in range(2):
        result = await backend.check("key", limit=3, window=10.0, now=100.0)
        assert result.allowed is True
    result = await backend.check("key", limit=3, window=10.0, now=100.0)
    assert result.allowed is False


@pytest.mark.skipif(not redis_available(), reason="Redis not available")
@pytest.mark.asyncio
async def test_redis_fixed_window_new_window(redis_backend: RedisBackend) -> None:
    backend = RedisBackend("redis://localhost:6379/0", algorithm="fixed_window")
    await backend.reset("key")
    for _ in range(3):
        await backend.check("key", limit=3, window=10.0, now=100.0)
    result = await backend.check("key", limit=3, window=10.0, now=110.0)
    assert result.allowed is True


@pytest.mark.skipif(not redis_available(), reason="Redis not available")
@pytest.mark.asyncio
async def test_redis_fixed_window_retry_after(redis_backend: RedisBackend) -> None:
    backend = RedisBackend("redis://localhost:6379/0", algorithm="fixed_window")
    await backend.reset("key")
    for _ in range(3):
        await backend.check("key", limit=3, window=10.0, now=100.0)
    result = await backend.check("key", limit=3, window=10.0, now=105.0)
    assert result.allowed is False
    assert result.retry_after is not None
    assert result.retry_after > 0


@pytest.mark.skipif(not redis_available(), reason="Redis not available")
@pytest.mark.asyncio
async def test_redis_gcra_allows(redis_backend: RedisBackend) -> None:
    backend = RedisBackend("redis://localhost:6379/0", algorithm="gcra")
    await backend.reset("key")
    result = await backend.check("key", limit=3, window=10.0, now=100.0)
    assert result.allowed is True
    assert result.remaining == 2


@pytest.mark.skipif(not redis_available(), reason="Redis not available")
@pytest.mark.asyncio
async def test_redis_gcra_blocks(redis_backend: RedisBackend) -> None:
    backend = RedisBackend("redis://localhost:6379/0", algorithm="gcra")
    await backend.reset("key")
    for _ in range(3):
        result = await backend.check("key", limit=3, window=10.0, now=100.0)
        assert result.allowed is True
    result = await backend.check("key", limit=3, window=10.0, now=100.0)
    assert result.allowed is False


@pytest.mark.skipif(not redis_available(), reason="Redis not available")
@pytest.mark.asyncio
async def test_redis_gcra_burst(redis_backend: RedisBackend) -> None:
    backend = RedisBackend("redis://localhost:6379/0", algorithm="gcra", burst=10)
    await backend.reset("key")
    for _ in range(10):
        result = await backend.check("key", limit=3, window=10.0, now=100.0)
        assert result.allowed is True
    result = await backend.check("key", limit=3, window=10.0, now=100.0)
    assert result.allowed is False


@pytest.mark.skipif(not redis_available(), reason="Redis not available")
@pytest.mark.asyncio
async def test_redis_gcra_reset(redis_backend: RedisBackend) -> None:
    backend = RedisBackend("redis://localhost:6379/0", algorithm="gcra")
    await backend.reset("key")
    for _ in range(3):
        await backend.check("key", limit=3, window=10.0, now=100.0)
    await backend.reset("key")
    result = await backend.check("key", limit=3, window=10.0, now=100.0)
    assert result.allowed is True


@pytest.mark.skipif(not redis_available(), reason="Redis not available")
@pytest.mark.asyncio
async def test_redis_sliding_window_log_retry_after(
    redis_backend: RedisBackend,
) -> None:
    for _ in range(3):
        await redis_backend.check("key", limit=3, window=10.0, now=100.0)
    result = await redis_backend.check("key", limit=3, window=10.0, now=100.0)
    assert result.allowed is False
    assert result.retry_after is not None
    assert result.retry_after > 0


@pytest.mark.skipif(not redis_available(), reason="Redis not available")
@pytest.mark.asyncio
async def test_from_url_redis() -> None:
    backend = from_url("redis://localhost:6379/0")
    assert isinstance(backend, RedisBackend)


def test_from_url_memory() -> None:
    from fastapi_sliding_window._backends.memory import InMemoryBackend

    backend = from_url("memory://")
    assert isinstance(backend, InMemoryBackend)
