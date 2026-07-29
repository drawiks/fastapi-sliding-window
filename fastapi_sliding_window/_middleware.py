from __future__ import annotations

from collections.abc import Callable
from time import monotonic
from typing import TYPE_CHECKING, Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from fastapi_sliding_window._backends.base import RateLimitBackend
from fastapi_sliding_window._exceptions import RateLimitExceeded
from fastapi_sliding_window._headers import rate_limit_headers
from fastapi_sliding_window._limits import parse
from fastapi_sliding_window._types import Algorithm, KeyFunc
from fastapi_sliding_window._utils import default_key_func, make_backend, resolve_key

if TYPE_CHECKING:
    from fastapi_sliding_window._limiter import Limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: Any,
        requests: int | str = 100,
        window_seconds: float = 60.0,
        algorithm: Algorithm = Algorithm.SLIDING_WINDOW_LOG,
        key_func: KeyFunc | None = None,
        include_headers: bool = True,
        exclude_paths: list[str] | None = None,
        detail: str = "Rate limit exceeded",
        backend: RateLimitBackend | None = None,
        cost: int | Callable[[Request], int] = 1,
        limiter: Limiter | None = None,
        use_ietf_headers: bool = False,
    ) -> None:
        super().__init__(app)
        self._limiter = limiter
        self._key_func = key_func
        self._include_headers = include_headers
        self._use_ietf = use_ietf_headers
        self._exclude_paths = set(exclude_paths or [])
        self._detail = detail
        self._cost = cost
        self._backend = backend

        if limiter is not None:
            limiter._include_headers = include_headers
            limiter._use_ietf = use_ietf_headers
            self._requests: int | None = None
            self._window_seconds = 0.0
            return

        self._algorithm = algorithm
        if isinstance(requests, str):
            item = parse(requests)
            self._requests = item.limit
            self._window_seconds = item.window
            self._burst = item.burst
        else:
            self._requests = requests
            self._window_seconds = window_seconds
            self._burst = None
        self._key_func = key_func or default_key_func
        if backend is not None:
            self._backend = backend
        else:
            self._backend = make_backend(algorithm, burst=self._burst)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self._exclude_paths:
            return await call_next(request)

        if self._limiter is not None:
            resp = Response()
            try:
                await self._limiter.check_rules(request, resp, [])
            except RateLimitExceeded as e:
                headers = dict(e.headers) if e.headers else {}
                return JSONResponse(
                    status_code=429,
                    content={"detail": self._detail},
                    headers=headers,
                )
            response = await call_next(request)
            if resp.headers:
                response.headers.update(resp.headers)
            return response

        key = await resolve_key(request, self._key_func or default_key_func)
        now = monotonic()
        resolved_cost = self._cost(request) if callable(self._cost) else self._cost
        assert self._requests is not None
        result = await (self._backend or make_backend(self._algorithm)).check(
            key, self._requests, self._window_seconds, now, cost=resolved_cost
        )

        if not result.allowed:
            headers = rate_limit_headers(result, self._use_ietf) if self._include_headers else {}
            return JSONResponse(
                status_code=429,
                content={"detail": self._detail},
                headers=headers,
            )

        response = await call_next(request)

        if self._include_headers:
            for header, value in rate_limit_headers(result, self._use_ietf).items():
                response.headers[header] = value

        return response
