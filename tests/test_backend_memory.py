from __future__ import annotations

import pytest
from fastapi_rate_limit._backends.memory import InMemoryBackend


@pytest.mark.asyncio
async def test_allows_requests_within_limit() -> None:
    backend = InMemoryBackend()
    result = await backend.check("key", limit=3, window=10.0, now=100.0)
    assert result.allowed is True
    assert result.remaining == 2


@pytest.mark.asyncio
async def test_blocks_after_limit() -> None:
    backend = InMemoryBackend()
    for i in range(3):
        await backend.check("key", limit=3, window=10.0, now=100.0 + i * 0.1)

    result = await backend.check("key", limit=3, window=10.0, now=100.5)
    assert result.allowed is False


@pytest.mark.asyncio
async def test_window_expiry() -> None:
    backend = InMemoryBackend()
    for i in range(3):
        await backend.check("key", limit=3, window=5.0, now=100.0)

    result = await backend.check("key", limit=3, window=5.0, now=105.1)
    assert result.allowed is True


@pytest.mark.asyncio
async def test_reset() -> None:
    backend = InMemoryBackend()
    for i in range(3):
        await backend.check("key", limit=3, window=10.0, now=100.0)

    await backend.reset("key")
    result = await backend.check("key", limit=3, window=10.0, now=100.1)
    assert result.allowed is True


@pytest.mark.asyncio
async def test_multiple_keys() -> None:
    backend = InMemoryBackend()
    await backend.check("a", limit=1, window=10.0, now=100.0)
    await backend.check("b", limit=1, window=10.0, now=100.0)

    result_a = await backend.check("a", limit=1, window=10.0, now=100.0)
    assert result_a.allowed is False

    result_b = await backend.check("b", limit=1, window=10.0, now=100.0)
    assert result_b.allowed is False


@pytest.mark.asyncio
async def test_concurrent_access() -> None:
    import asyncio

    backend = InMemoryBackend()

    async def make_request() -> bool:
        result = await backend.check("key", limit=10, window=60.0, now=100.0)
        return result.allowed

    results = await asyncio.gather(*[make_request() for _ in range(20)])
    allowed_count = sum(1 for r in results if r)
    assert allowed_count == 10
