from __future__ import annotations

from collections.abc import Awaitable

from starlette.requests import Request

from fastapi_rate_limit._algorithms.fixed_window import FixedWindowBackend
from fastapi_rate_limit._algorithms.sliding_window_counter import SlidingWindowCounterBackend
from fastapi_rate_limit._algorithms.sliding_window_log import SlidingWindowLogBackend
from fastapi_rate_limit._backends.base import RateLimitBackend
from fastapi_rate_limit._types import Algorithm, KeyFunc


def default_key_func(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def make_backend(algorithm: Algorithm) -> RateLimitBackend:
    if algorithm == Algorithm.SLIDING_WINDOW_LOG:
        return SlidingWindowLogBackend()
    if algorithm == Algorithm.SLIDING_WINDOW_COUNTER:
        return SlidingWindowCounterBackend()
    if algorithm == Algorithm.FIXED_WINDOW:
        return FixedWindowBackend()
    raise ValueError(f"Unknown algorithm: {algorithm}")


async def resolve_key(request: Request, key_func: KeyFunc) -> str:
    result = key_func(request)
    if isinstance(result, Awaitable):
        return await result
    return result
