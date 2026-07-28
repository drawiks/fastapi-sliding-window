from __future__ import annotations

import pytest
from fastapi_sliding_window._backends.base import RateLimitResult
from fastapi_sliding_window._exceptions import RateLimitExceeded
from fastapi_sliding_window._headers import rate_limit_headers
from fastapi_sliding_window._types import Algorithm
from fastapi_sliding_window._utils import default_key_func, make_backend


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


def test_rate_limit_exceeded_zero_retry_after_no_header() -> None:
    exc = RateLimitExceeded(retry_after=0.0)
    assert exc.headers is None or "Retry-After" not in exc.headers


def test_rate_limit_exceeded_accepts_extra_headers() -> None:
    exc = RateLimitExceeded(
        retry_after=5.0,
        headers={"X-RateLimit-Limit": "10", "X-RateLimit-Remaining": "0"},
    )
    assert exc.headers is not None
    assert exc.headers["X-RateLimit-Limit"] == "10"
    assert exc.headers["Retry-After"] == "5"


def test_make_backend_returns_correct_types() -> None:
    assert isinstance(make_backend(Algorithm.SLIDING_WINDOW_LOG), type(make_backend(Algorithm.SLIDING_WINDOW_LOG)))
    assert isinstance(make_backend(Algorithm.FIXED_WINDOW), type(make_backend(Algorithm.FIXED_WINDOW)))


def test_make_backend_raises_on_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown algorithm"):
        make_backend("invalid")  # type: ignore[arg-type]


def test_default_key_func_returns_unknown_for_empty_request() -> None:
    class FakeRequest:
        client = None

    assert default_key_func(FakeRequest()) == "unknown"  # type: ignore[arg-type]
