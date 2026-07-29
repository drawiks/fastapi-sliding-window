from __future__ import annotations

import pytest

from fastapi_sliding_window._backends.base import RateLimitResult
from fastapi_sliding_window._exceptions import RateLimitExceeded
from fastapi_sliding_window._headers import rate_limit_headers
from fastapi_sliding_window._types import Algorithm
from fastapi_sliding_window._utils import make_backend


def test_headers_include_all_fields() -> None:
    result = RateLimitResult(
        allowed=True,
        remaining=5,
        limit=10,
        reset_at=1000.0,
    )
    headers = rate_limit_headers(result)

    assert headers["X-RateLimit-Limit"] == "10"
    assert headers["X-RateLimit-Remaining"] == "5"
    assert headers["X-RateLimit-Reset"] == "1000"
    assert "Retry-After" not in headers


def test_headers_with_retry_after() -> None:
    result = RateLimitResult(
        allowed=False,
        remaining=0,
        limit=10,
        reset_at=1000.0,
        retry_after=5.0,
    )
    headers = rate_limit_headers(result)

    assert headers["Retry-After"] == "5"
    assert headers["X-RateLimit-Remaining"] == "0"


def test_headers_with_zero_retry_after() -> None:
    result = RateLimitResult(
        allowed=False,
        remaining=0,
        limit=10,
        reset_at=1000.0,
        retry_after=0.0,
    )
    headers = rate_limit_headers(result)

    assert headers["Retry-After"] == "0"


def test_headers_with_none_retry_after() -> None:
    result = RateLimitResult(
        allowed=True,
        remaining=9,
        limit=10,
        reset_at=1000.0,
        retry_after=None,
    )
    headers = rate_limit_headers(result)

    assert "Retry-After" not in headers


def test_rate_limit_exceeded_sets_retry_after_header() -> None:
    exc = RateLimitExceeded(retry_after=5.0)
    assert exc.status_code == 429
    assert exc.detail == "Rate limit exceeded"
    assert exc.headers is not None
    assert exc.headers["Retry-After"] == "5"


def test_rate_limit_exceeded_custom_detail() -> None:
    exc = RateLimitExceeded(retry_after=5.0, detail="Too many requests")
    assert exc.detail == "Too many requests"


def test_rate_limit_exceeded_zero_retry_after_sets_header() -> None:
    exc = RateLimitExceeded(retry_after=0.0)
    assert exc.headers is not None
    assert exc.headers["Retry-After"] == "0"


def test_rate_limit_exceeded_accepts_extra_headers() -> None:
    exc = RateLimitExceeded(
        retry_after=5.0,
        headers={"X-RateLimit-Limit": "10", "X-RateLimit-Remaining": "0"},
    )
    assert exc.headers is not None
    assert exc.headers["X-RateLimit-Limit"] == "10"
    assert exc.headers["Retry-After"] == "5"


def test_make_backend_returns_correct_types() -> None:
    from fastapi_sliding_window._algorithms.fixed_window import FixedWindowBackend
    from fastapi_sliding_window._algorithms.gcra import GCRABackend
    from fastapi_sliding_window._algorithms.sliding_window_counter import (
        SlidingWindowCounterBackend,
    )
    from fastapi_sliding_window._algorithms.sliding_window_log import (
        SlidingWindowLogBackend,
    )
    from fastapi_sliding_window._algorithms.token_bucket import TokenBucketBackend

    assert isinstance(make_backend(Algorithm.SLIDING_WINDOW_LOG), SlidingWindowLogBackend)
    assert isinstance(make_backend(Algorithm.FIXED_WINDOW), FixedWindowBackend)
    assert isinstance(make_backend(Algorithm.SLIDING_WINDOW_COUNTER), SlidingWindowCounterBackend)
    assert isinstance(make_backend(Algorithm.GCRA, burst=10), GCRABackend)
    assert isinstance(make_backend(Algorithm.TOKEN_BUCKET, burst=10), TokenBucketBackend)


def test_make_backend_raises_on_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown algorithm"):
        make_backend("invalid")  # type: ignore[arg-type]


def test_ietf_headers_use_correct_names() -> None:
    result = RateLimitResult(allowed=True, remaining=5, limit=10, reset_at=1000.0)
    headers = rate_limit_headers(result, use_ietf=True)

    assert "RateLimit-Limit" in headers
    assert "RateLimit-Remaining" in headers
    assert "RateLimit-Reset" in headers
    assert "X-RateLimit-Limit" not in headers
    assert headers["RateLimit-Limit"] == "10"
    assert headers["RateLimit-Remaining"] == "5"
    assert headers["RateLimit-Reset"] == "1000"


def test_ietf_headers_with_retry_after() -> None:
    result = RateLimitResult(
        allowed=False,
        remaining=0,
        limit=10,
        reset_at=1000.0,
        retry_after=5.0,
    )
    headers = rate_limit_headers(result, use_ietf=True)

    assert headers["RateLimit-Limit"] == "10"
    assert headers["Retry-After"] == "5"


def test_ietf_headers_no_retry_after_when_none() -> None:
    result = RateLimitResult(allowed=True, remaining=9, limit=10, reset_at=1000.0, retry_after=None)
    headers = rate_limit_headers(result, use_ietf=True)

    assert "Retry-After" not in headers
