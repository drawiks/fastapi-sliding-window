from __future__ import annotations

from fastapi import HTTPException


class RateLimitExceeded(HTTPException):
    def __init__(self, retry_after: float | int, detail: str = "Rate limit exceeded") -> None:
        import math

        headers = {"Retry-After": str(math.ceil(retry_after))} if retry_after > 0 else {}
        super().__init__(status_code=429, detail=detail, headers=headers)
        self.retry_after = retry_after
