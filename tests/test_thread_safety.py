from __future__ import annotations

import asyncio

import pytest

from fastapi_sliding_window._algorithms.fixed_window import FixedWindowBackend
from fastapi_sliding_window._algorithms.gcra import GCRABackend
from fastapi_sliding_window._algorithms.sliding_window_counter import (
    SlidingWindowCounterBackend,
)
from fastapi_sliding_window._algorithms.sliding_window_log import (
    SlidingWindowLogBackend,
)
from fastapi_sliding_window._algorithms.token_bucket import TokenBucketBackend
from fastapi_sliding_window._backends.memory import InMemoryBackend


@pytest.mark.asyncio
async def test_concurrent_sliding_window_log() -> None:
    backend = SlidingWindowLogBackend()

    async def make_request() -> bool:
        result = await backend.check("key", limit=10, window=60.0, now=100.0)
        return result.allowed

    tasks = [make_request() for _ in range(20)]
    results = await asyncio.gather(*tasks)
    allowed_count = sum(1 for r in results if r)
    assert allowed_count == 10


@pytest.mark.asyncio
async def test_concurrent_in_memory_backend() -> None:
    backend = InMemoryBackend()

    async def make_request() -> bool:
        result = await backend.check("key", limit=10, window=60.0, now=100.0)
        return result.allowed

    tasks = [make_request() for _ in range(20)]
    results = await asyncio.gather(*tasks)
    allowed_count = sum(1 for r in results if r)
    assert allowed_count == 10


@pytest.mark.asyncio
async def test_concurrent_different_keys() -> None:
    backend = InMemoryBackend()

    async def make_request(key: str) -> bool:
        result = await backend.check(key, limit=5, window=60.0, now=100.0)
        return result.allowed

    tasks = [make_request(f"key_{i}") for i in range(30)]
    results = await asyncio.gather(*tasks)
    allowed_count = sum(1 for r in results if r)
    assert allowed_count == 30


@pytest.mark.asyncio
async def test_concurrent_sliding_window_counter() -> None:
    backend = SlidingWindowCounterBackend()

    async def make_request() -> bool:
        result = await backend.check("key", limit=10, window=60.0, now=100.0)
        return result.allowed

    tasks = [make_request() for _ in range(20)]
    results = await asyncio.gather(*tasks)
    allowed_count = sum(1 for r in results if r)
    assert allowed_count == 10


@pytest.mark.asyncio
async def test_concurrent_fixed_window() -> None:
    backend = FixedWindowBackend()

    async def make_request() -> bool:
        result = await backend.check("key", limit=10, window=60.0, now=100.0)
        return result.allowed

    tasks = [make_request() for _ in range(20)]
    results = await asyncio.gather(*tasks)
    allowed_count = sum(1 for r in results if r)
    assert allowed_count == 10


@pytest.mark.asyncio
async def test_concurrent_token_bucket() -> None:
    backend = TokenBucketBackend()

    async def make_request() -> bool:
        result = await backend.check("key", limit=10, window=60.0, now=100.0)
        return result.allowed

    tasks = [make_request() for _ in range(20)]
    results = await asyncio.gather(*tasks)
    allowed_count = sum(1 for r in results if r)
    assert allowed_count == 10


@pytest.mark.asyncio
async def test_concurrent_gcra() -> None:
    backend = GCRABackend()

    async def make_request() -> bool:
        result = await backend.check("key", limit=10, window=60.0, now=100.0)
        return result.allowed

    tasks = [make_request() for _ in range(20)]
    results = await asyncio.gather(*tasks)
    allowed_count = sum(1 for r in results if r)
    assert allowed_count == 10


@pytest.mark.asyncio
async def test_concurrent_gcra_burst() -> None:
    backend = GCRABackend(burst=20)

    async def make_request() -> bool:
        result = await backend.check("key", limit=10, window=60.0, now=100.0)
        return result.allowed

    tasks = [make_request() for _ in range(30)]
    results = await asyncio.gather(*tasks)
    allowed_count = sum(1 for r in results if r)
    assert allowed_count == 20
