from __future__ import annotations

import math

from fastapi import HTTPException


class RateLimitExceeded(HTTPException):
    def __init__(
        self,
        retry_after: float = 0.0,
        detail: str = "Rate limit exceeded",
        headers: dict[str, str] | None = None,
    ) -> None:
        merged = dict(headers or {})
        if "Retry-After" not in merged and retry_after > 0:
            merged["Retry-After"] = str(math.ceil(retry_after))
        super().__init__(status_code=429, detail=detail, headers=merged or None)
        self.retry_after = retry_after
