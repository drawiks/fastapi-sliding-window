from __future__ import annotations

import time

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
    ) -> None:
        self._requests = requests
        self._window_seconds = window_seconds
        self._algorithm = algorithm
        self._key_func = key_func or default_key_func
        self._include_headers = include_headers
        self._backend = make_backend(algorithm)

    async def __call__(self, request: Request, response: Response) -> None:
        key = await resolve_key(request, self._key_func)
        now = time.monotonic()
        result = await self._backend.check(key, self._requests, self._window_seconds, now)

        if self._include_headers:
            for header, value in rate_limit_headers(result).items():
                response.headers[header] = value

        if not result.allowed:
            raise RateLimitExceeded(retry_after=result.retry_after or 0.0)
