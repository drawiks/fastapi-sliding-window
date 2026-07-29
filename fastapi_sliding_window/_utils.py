from __future__ import annotations

from collections.abc import Awaitable

from starlette.requests import Request

from fastapi_sliding_window._algorithms.fixed_window import FixedWindowBackend
from fastapi_sliding_window._algorithms.gcra import GCRABackend
from fastapi_sliding_window._algorithms.sliding_window_counter import (
    SlidingWindowCounterBackend,
)
from fastapi_sliding_window._algorithms.sliding_window_log import (
    SlidingWindowLogBackend,
)
from fastapi_sliding_window._algorithms.token_bucket import TokenBucketBackend
from fastapi_sliding_window._backends.base import RateLimitBackend
from fastapi_sliding_window._types import Algorithm, KeyFunc


def default_key_func(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def make_backend(algorithm: Algorithm, burst: int | None = None, max_keys: int = 10000) -> RateLimitBackend:
    if algorithm == Algorithm.SLIDING_WINDOW_LOG:
        return SlidingWindowLogBackend(max_keys=max_keys)
    if algorithm == Algorithm.SLIDING_WINDOW_COUNTER:
        return SlidingWindowCounterBackend(max_keys=max_keys)
    if algorithm == Algorithm.FIXED_WINDOW:
        return FixedWindowBackend(max_keys=max_keys)
    if algorithm == Algorithm.GCRA:
        return GCRABackend(burst=burst, max_keys=max_keys)
    if algorithm == Algorithm.TOKEN_BUCKET:
        return TokenBucketBackend(burst=burst, max_keys=max_keys)
    raise ValueError(f"Unknown algorithm: {algorithm}")


def from_url(
    url: str,
    algorithm: str = "sliding_window_log",
    key_prefix: str = "rl:",
    burst: int | None = None,
    max_keys: int = 10000,
) -> RateLimitBackend:
    if url.startswith(("redis://", "rediss://", "redis+unix://")):
        from fastapi_sliding_window._backends.redis import RedisBackend

        return RedisBackend(url, algorithm=algorithm, key_prefix=key_prefix, burst=burst)
    if url == "memory://":
        from fastapi_sliding_window._backends.memory import InMemoryBackend

        return InMemoryBackend(
            algorithm=Algorithm(algorithm) if isinstance(algorithm, str) else algorithm,
            burst=burst,
            max_keys=max_keys,
        )
    raise ValueError(f"Unknown backend URL: {url!r}")


async def resolve_key(request: Request, key_func: KeyFunc) -> str:
    result = key_func(request)
    if isinstance(result, Awaitable):
        return await result
    return result
