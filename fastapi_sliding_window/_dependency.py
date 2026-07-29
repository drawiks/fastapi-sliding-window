from __future__ import annotations

from collections.abc import Callable
from time import monotonic
from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import Response

from fastapi_sliding_window._backends.base import RateLimitBackend
from fastapi_sliding_window._exceptions import RateLimitExceeded
from fastapi_sliding_window._headers import rate_limit_headers
from fastapi_sliding_window._limits import parse
from fastapi_sliding_window._types import Algorithm, KeyFunc
from fastapi_sliding_window._utils import default_key_func, make_backend, resolve_key

if TYPE_CHECKING:
    from fastapi_sliding_window._limiter import Limiter


class RateLimit:
    def __init__(
        self,
        requests: int | str = 100,
        window_seconds: float = 60.0,
        algorithm: Algorithm = Algorithm.SLIDING_WINDOW_LOG,
        key_func: KeyFunc | None = None,
        include_headers: bool = True,
        detail: str = "Rate limit exceeded",
        backend: RateLimitBackend | None = None,
        cost: int | Callable[[Request], int] = 1,
        limiter: Limiter | None = None,
        use_ietf_headers: bool = False,
    ) -> None:
        self._limiter = limiter
        self._include_headers = include_headers
        self._use_ietf = use_ietf_headers
        self._backend = backend
        self._detail = detail
        self._cost = cost

        if limiter is not None:
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

    async def __call__(self, request: Request, response: Response) -> None:
        if self._limiter is not None:
            endpoint = request.scope.get("endpoint")
            rules = getattr(endpoint, "__rate_limit_rules__", []) if endpoint else []
            await self._limiter.check_rules(
                request,
                response,
                rules,
                include_headers=self._include_headers,
                use_ietf=self._use_ietf,
            )
            return

        key = await resolve_key(request, self._key_func)
        now = monotonic()
        resolved_cost = self._cost(request) if callable(self._cost) else self._cost
        assert self._requests is not None
        assert self._backend is not None
        result = await self._backend.check(key, self._requests, self._window_seconds, now, cost=resolved_cost)

        if not result.allowed:
            headers = rate_limit_headers(result, self._use_ietf) if self._include_headers else {}
            raise RateLimitExceeded(
                retry_after=result.retry_after or 0.0,
                detail=self._detail,
                headers=headers,
            )

        if self._include_headers:
            for header, value in rate_limit_headers(result, self._use_ietf).items():
                response.headers[header] = value
