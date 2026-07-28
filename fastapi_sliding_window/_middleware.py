from __future__ import annotations

from time import monotonic
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from fastapi_sliding_window._headers import rate_limit_headers
from fastapi_sliding_window._types import Algorithm, KeyFunc
from fastapi_sliding_window._utils import default_key_func, make_backend, resolve_key


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: Any,
        requests: int = 100,
        window_seconds: float = 60.0,
        algorithm: Algorithm = Algorithm.SLIDING_WINDOW_LOG,
        key_func: KeyFunc | None = None,
        include_headers: bool = True,
        exclude_paths: list[str] | None = None,
        detail: str = "Rate limit exceeded",
    ) -> None:
        super().__init__(app)
        self._requests = requests
        self._window_seconds = window_seconds
        self._backend = make_backend(algorithm)
        self._key_func = key_func or default_key_func
        self._include_headers = include_headers
        self._exclude_paths = set(exclude_paths or [])
        self._detail = detail

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self._exclude_paths:
            return await call_next(request)

        key = await resolve_key(request, self._key_func)
        now = monotonic()
        result = await self._backend.check(key, self._requests, self._window_seconds, now)

        if not result.allowed:
            headers = rate_limit_headers(result) if self._include_headers else {}
            return JSONResponse(
                status_code=429,
                content={"detail": self._detail},
                headers=headers,
            )

        response = await call_next(request)

        if self._include_headers:
            for header, value in rate_limit_headers(result).items():
                response.headers[header] = value

        return response
