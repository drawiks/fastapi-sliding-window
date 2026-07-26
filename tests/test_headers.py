from __future__ import annotations

from fastapi_rate_limit._backends.base import RateLimitResult
from fastapi_rate_limit._headers import rate_limit_headers


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
