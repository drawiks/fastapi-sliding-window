from __future__ import annotations

import json
import warnings
from collections.abc import Callable, MutableMapping
from time import monotonic
from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from fastapi_sliding_window._backends.base import RateLimitBackend
from fastapi_sliding_window._exceptions import RateLimitExceeded
from fastapi_sliding_window._headers import rate_limit_headers
from fastapi_sliding_window._limits import parse
from fastapi_sliding_window._types import Algorithm, KeyFunc
from fastapi_sliding_window._utils import default_key_func, make_backend, resolve_key

if TYPE_CHECKING:
    from fastapi_sliding_window._limiter import Limiter


class RateLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
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
        exempt_when: Callable[[Request], bool] | None = None,
    ) -> None:
        self.app = app
        self._limiter = limiter
        self._key_func = key_func
        self._include_headers = include_headers
        self._use_ietf = use_ietf_headers
        self._exclude_paths = set(exclude_paths or [])
        self._detail = detail
        self._cost = cost
        self._backend = backend
        self._exempt_when = exempt_when

        if limiter is not None:
            self._requests: int | None = None
            self._window_seconds = 0.0
            if not limiter._default_limits:
                warnings.warn(
                    "RateLimitMiddleware with limiter but no default_limits: "
                    "endpoint @limiter.limit() decorators won't apply. "
                    "Use Depends(RateLimit(limiter=limiter)) for per-endpoint limits.",
                    stacklevel=2,
                )
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

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")
        if path in self._exclude_paths:
            await self.app(scope, receive, send)
            return

        request = Request(scope)

        if self._exempt_when is not None and self._exempt_when(request):
            await self.app(scope, receive, send)
            return

        if self._limiter is not None:
            await self._handle_limiter_mode(scope, receive, send, request)
            return

        await self._handle_direct_mode(scope, receive, send, request)

    async def _handle_limiter_mode(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        request: Request,
    ) -> None:
        assert self._limiter is not None
        resp = Response()
        try:
            await self._limiter.check_rules(
                request,
                resp,
                [],
                include_headers=self._include_headers,
                use_ietf=self._use_ietf,
            )
        except RateLimitExceeded as e:
            await self._send_429(send, self._detail, dict(e.headers) if e.headers else None)
            return

        extra_headers: dict[str, str] = dict(resp.headers) if resp.headers else {}

        async def send_wrapper(message: MutableMapping[str, Any]) -> None:
            if message["type"] == "http.response.start" and extra_headers:
                headers = list(message.get("headers", []))
                for name, value in extra_headers.items():
                    headers.append((name.encode("utf-8"), value.encode("utf-8")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)

    async def _handle_direct_mode(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        request: Request,
    ) -> None:
        key = await resolve_key(request, self._key_func or default_key_func)
        now = monotonic()
        resolved_cost = self._cost(request) if callable(self._cost) else self._cost
        assert self._requests is not None

        assert self._backend is not None
        result = await self._backend.check(key, self._requests, self._window_seconds, now, cost=resolved_cost)

        if not result.allowed:
            headers = rate_limit_headers(result, self._use_ietf) if self._include_headers else {}
            await self._send_429(send, self._detail, headers)
            return

        if self._include_headers:
            extra_headers: dict[str, str] = rate_limit_headers(result, self._use_ietf)

            async def send_wrapper(message: MutableMapping[str, Any]) -> None:
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    for name, value in extra_headers.items():
                        headers.append((name.encode("utf-8"), value.encode("utf-8")))
                    message["headers"] = headers
                await send(message)

            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)

    @staticmethod
    async def _send_429(
        send: Send,
        detail: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        raw_headers = [(b"content-type", b"application/json")]
        if headers:
            for name, value in headers.items():
                raw_headers.append((name.encode("utf-8"), value.encode("utf-8")))
        await send(
            {
                "type": "http.response.start",
                "status": 429,
                "headers": raw_headers,
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": json.dumps({"detail": detail}).encode("utf-8"),
            }
        )
