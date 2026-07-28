from __future__ import annotations

from time import monotonic

from starlette.requests import Request
from starlette.responses import Response

from fastapi_sliding_window._exceptions import RateLimitExceeded
from fastapi_sliding_window._headers import rate_limit_headers
from fastapi_sliding_window._types import Algorithm, KeyFunc
from fastapi_sliding_window._utils import default_key_func, make_backend, resolve_key


class RateLimit:
    def __init__(
        self,
        requests: int,
        window_seconds: float,
        algorithm: Algorithm = Algorithm.SLIDING_WINDOW_LOG,
        key_func: KeyFunc | None = None,
        include_headers: bool = True,
        detail: str = "Rate limit exceeded",
    ) -> None:
        self._requests = requests
        self._window_seconds = window_seconds
        self._key_func = key_func or default_key_func
        self._include_headers = include_headers
        self._detail = detail
        self._backend = make_backend(algorithm)

    async def __call__(self, request: Request, response: Response) -> None:
        key = await resolve_key(request, self._key_func)
        now = monotonic()
        result = await self._backend.check(key, self._requests, self._window_seconds, now)

        if not result.allowed:
            headers = rate_limit_headers(result) if self._include_headers else {}
            raise RateLimitExceeded(retry_after=result.retry_after or 0.0, detail=self._detail, headers=headers)

        if self._include_headers:
            for header, value in rate_limit_headers(result).items():
                response.headers[header] = value
