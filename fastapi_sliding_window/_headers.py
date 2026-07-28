from __future__ import annotations

from math import ceil

from fastapi_sliding_window._backends.base import RateLimitResult


def rate_limit_headers(result: RateLimitResult) -> dict[str, str]:
    headers: dict[str, str] = {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
        "X-RateLimit-Reset": str(int(result.reset_at)),
    }
    if result.retry_after is not None:
        headers["Retry-After"] = str(ceil(result.retry_after))
    return headers
