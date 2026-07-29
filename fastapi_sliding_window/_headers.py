from __future__ import annotations

from math import ceil

from fastapi_sliding_window._backends.base import RateLimitResult


def rate_limit_headers(result: RateLimitResult, use_ietf: bool = False) -> dict[str, str]:
    headers: dict[str, str] = {}
    if use_ietf:
        headers["RateLimit-Limit"] = str(result.limit)
        headers["RateLimit-Remaining"] = str(result.remaining)
        headers["RateLimit-Reset"] = str(int(result.reset_at))
    else:
        headers["X-RateLimit-Limit"] = str(result.limit)
        headers["X-RateLimit-Remaining"] = str(result.remaining)
        headers["X-RateLimit-Reset"] = str(int(result.reset_at))
    if result.retry_after is not None:
        headers["Retry-After"] = str(ceil(result.retry_after))
    return headers
