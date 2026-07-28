from __future__ import annotations

import pytest
from fastapi_sliding_window._algorithms.fixed_window import FixedWindowBackend
from fastapi_sliding_window._algorithms.sliding_window_counter import SlidingWindowCounterBackend
from fastapi_sliding_window._algorithms.sliding_window_log import SlidingWindowLogBackend


@pytest.mark.asyncio
async def test_allows_requests_within_limit() -> None:
    backend = SlidingWindowLogBackend()
    result = await backend.check("key", limit=3, window=10.0, now=100.0)
    assert result.allowed is True
    assert result.remaining == 2
    assert result.limit == 3


@pytest.mark.asyncio
async def test_blocks_after_limit_exceeded() -> None:
    backend = SlidingWindowLogBackend()
    for i in range(3):
        result = await backend.check("key", limit=3, window=10.0, now=100.0 + i * 0.1)
        assert result.allowed is True

    result = await backend.check("key", limit=3, window=10.0, now=100.3)
    assert result.allowed is False
    assert result.remaining == 0
    assert result.retry_after is not None


@pytest.mark.asyncio
async def test_window_expiry_allows_new_requests() -> None:
    backend = SlidingWindowLogBackend()
    for i in range(3):
        await backend.check("key", limit=3, window=10.0, now=100.0 + i * 0.1)

    result = await backend.check("key", limit=3, window=10.0, now=110.1)
    assert result.allowed is True
    assert result.remaining == 1


@pytest.mark.asyncio
async def test_reset_clears_key() -> None:
    backend = SlidingWindowLogBackend()
    for i in range(3):
        await backend.check("key", limit=3, window=10.0, now=100.0)

    await backend.reset("key")
    result = await backend.check("key", limit=3, window=10.0, now=100.1)
    assert result.allowed is True
    assert result.remaining == 2


@pytest.mark.asyncio
async def test_different_keys_are_independent() -> None:
    backend = SlidingWindowLogBackend()
    for i in range(3):
        await backend.check("a", limit=3, window=10.0, now=100.0)

    result_a = await backend.check("a", limit=3, window=10.0, now=100.0)
    assert result_a.allowed is False

    result_b = await backend.check("b", limit=3, window=10.0, now=100.0)
    assert result_b.allowed is True
    assert result_b.remaining == 2


@pytest.mark.asyncio
async def test_remaining_count_accurate() -> None:
    backend = SlidingWindowLogBackend()
    result = await backend.check("k", limit=5, window=60.0, now=100.0)
    assert result.remaining == 4

    result = await backend.check("k", limit=5, window=60.0, now=100.1)
    assert result.remaining == 3

    result = await backend.check("k", limit=5, window=60.0, now=100.2)
    assert result.remaining == 2


@pytest.mark.asyncio
async def test_reset_at_is_correct() -> None:
    backend = SlidingWindowLogBackend()
    result = await backend.check("k", limit=5, window=60.0, now=100.0)
    assert result.reset_at == 160


@pytest.mark.asyncio
async def test_retry_after_calculation() -> None:
    backend = SlidingWindowLogBackend()
    for i in range(3):
        await backend.check("k", limit=3, window=10.0, now=100.0 + i * 0.5)

    result = await backend.check("k", limit=3, window=10.0, now=100.0)
    assert result.allowed is False
    assert result.retry_after is not None
    assert result.retry_after > 0


@pytest.mark.asyncio
async def test_fixed_window_allows_requests_within_limit() -> None:
    backend = FixedWindowBackend()
    result = await backend.check("key", limit=3, window=10.0, now=100.0)
    assert result.allowed is True
    assert result.remaining == 2


@pytest.mark.asyncio
async def test_fixed_window_reset_at_uses_window_start() -> None:
    backend = FixedWindowBackend()
    result = await backend.check("key", limit=5, window=60.0, now=100.0)
    assert result.reset_at == 120  # window_start=60 + window=60


@pytest.mark.asyncio
async def test_sliding_window_counter_allows_requests_within_limit() -> None:
    backend = SlidingWindowCounterBackend()
    result = await backend.check("key", limit=3, window=10.0, now=100.0)
    assert result.allowed is True


@pytest.mark.asyncio
async def test_sliding_window_counter_blocks_after_limit() -> None:
    backend = SlidingWindowCounterBackend()
    for i in range(3):
        result = await backend.check("key", limit=3, window=10.0, now=100.0 + i * 0.1)
        assert result.allowed is True
    result = await backend.check("key", limit=3, window=10.0, now=100.5)
    assert result.allowed is False


@pytest.mark.asyncio
async def test_fixed_window_blocks_after_limit() -> None:
    backend = FixedWindowBackend()
    for _ in range(3):
        result = await backend.check("key", limit=3, window=10.0, now=100.0)
        assert result.allowed is True
    result = await backend.check("key", limit=3, window=10.0, now=100.0)
    assert result.allowed is False


@pytest.mark.asyncio
async def test_fixed_window_reset_clears_key() -> None:
    backend = FixedWindowBackend()
    for _ in range(3):
        await backend.check("key", limit=3, window=10.0, now=100.0)
    await backend.reset("key")
    result = await backend.check("key", limit=3, window=10.0, now=100.0)
    assert result.allowed is True


@pytest.mark.asyncio
async def test_sliding_window_counter_reset_clears_key() -> None:
    backend = SlidingWindowCounterBackend()
    for i in range(3):
        await backend.check("key", limit=3, window=10.0, now=100.0 + i * 0.1)
    await backend.reset("key")
    result = await backend.check("key", limit=3, window=10.0, now=100.0)
    assert result.allowed is True
