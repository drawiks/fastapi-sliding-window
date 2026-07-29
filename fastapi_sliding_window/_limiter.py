from __future__ import annotations

from collections.abc import Callable
from time import monotonic
from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import Response

from fastapi_sliding_window._backends.base import RateLimitResult
from fastapi_sliding_window._exceptions import RateLimitExceeded
from fastapi_sliding_window._headers import rate_limit_headers
from fastapi_sliding_window._limits import RateLimitItem, parse_many
from fastapi_sliding_window._types import KeyFunc
from fastapi_sliding_window._utils import default_key_func, resolve_key

if TYPE_CHECKING:
    from fastapi_sliding_window._backends.base import RateLimitBackend


class Limiter:
    def __init__(
        self,
        backend: RateLimitBackend,
        key_func: KeyFunc = default_key_func,
        default_limits: list[str] | None = None,
        on_breach: Callable[[Request, RateLimitExceeded], Response] | None = None,
        include_headers: bool = True,
        use_ietf_headers: bool = False,
    ) -> None:
        self._backend = backend
        self._key_func = key_func
        self._default_limits = [parse_many(s) for s in (default_limits or [])]
        self._on_breach = on_breach
        self._include_headers = include_headers
        self._use_ietf = use_ietf_headers

    def limit(
        self,
        limit_str: str,
        cost: int | Callable[[Request], int] = 1,
        key_func: KeyFunc | None = None,
        exempt_when: Callable[[Request], bool] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        items = parse_many(limit_str)

        def decorator(endpoint: Callable[..., Any]) -> Callable[..., Any]:
            existing = getattr(endpoint, "__rate_limit_rules__", [])
            updated = [(items, cost, key_func, exempt_when)] + existing
            endpoint.__rate_limit_rules__ = updated  # type: ignore[attr-defined]
            flat = [item for rule in updated for item in rule[0]]
            endpoint.__rate_limit_items__ = flat  # type: ignore[attr-defined]
            return endpoint

        return decorator

    def exempt(self, endpoint: Callable[..., Any]) -> Callable[..., Any]:
        endpoint._rate_limit_exempt = True  # type: ignore[attr-defined]
        return endpoint

    async def check(
        self,
        request: Request,
        response: Response,
        items: list[RateLimitItem],
        cost: int | Callable[[Request], int] = 1,
        key_func: KeyFunc | None = None,
        *,
        include_headers: bool | None = None,
        use_ietf: bool | None = None,
    ) -> None:
        if getattr(request.scope.get("endpoint"), "_rate_limit_exempt", False):
            return
        key = await resolve_key(request, key_func or self._key_func)
        all_items = list(items)
        for defaults in self._default_limits:
            all_items.extend(defaults)
        result = await self._check_items(request, response, key, all_items, cost)
        effective_include = include_headers if include_headers is not None else self._include_headers
        effective_ietf = use_ietf if use_ietf is not None else self._use_ietf
        if effective_include and result is not None:
            for h, v in rate_limit_headers(result, effective_ietf).items():
                response.headers[h] = v

    async def check_rules(
        self,
        request: Request,
        response: Response,
        rules: list[
            tuple[
                list[RateLimitItem],
                int | Callable[[Request], int],
                KeyFunc | None,
                Callable[[Request], bool] | None,
            ]
        ],
        *,
        include_headers: bool | None = None,
        use_ietf: bool | None = None,
    ) -> None:
        effective_include = include_headers if include_headers is not None else self._include_headers
        effective_ietf = use_ietf if use_ietf is not None else self._use_ietf
        if getattr(request.scope.get("endpoint"), "_rate_limit_exempt", False):
            return
        had_rule = False
        result = None
        _key_cache: dict[KeyFunc, str] = {}
        for items, cost, key_func, exempt_when in rules:
            had_rule = True
            if exempt_when and exempt_when(request):
                continue
            kf = key_func or self._key_func
            if kf not in _key_cache:
                _key_cache[kf] = await resolve_key(request, kf)
            key = _key_cache[kf]
            all_items = list(items)
            for defaults in self._default_limits:
                all_items.extend(defaults)
            if not all_items:
                continue
            result = await self._check_items(request, response, key, all_items, cost, effective_include, effective_ietf)
        if not had_rule and self._default_limits:
            kf = self._key_func
            if kf not in _key_cache:
                _key_cache[kf] = await resolve_key(request, kf)
            key = _key_cache[kf]
            for defaults in self._default_limits:
                if defaults:
                    result = await self._check_items(
                        request, response, key, defaults, 1, effective_include, effective_ietf
                    )
        if effective_include and result is not None:
            for h, v in rate_limit_headers(result, effective_ietf).items():
                response.headers[h] = v

    async def _check_items(
        self,
        request: Request,
        response: Response,
        key: str,
        items: list[RateLimitItem],
        cost: int | Callable[[Request], int],
        include_headers: bool | None = None,
        use_ietf: bool | None = None,
    ) -> RateLimitResult | None:
        now = monotonic()
        resolved_cost = cost(request) if callable(cost) else cost
        effective_include = include_headers if include_headers is not None else self._include_headers
        effective_ietf = use_ietf if use_ietf is not None else self._use_ietf
        merged: RateLimitResult | None = None
        for item in items:
            item_key = f"{key}:{item.limit}:{item.window}"
            result = await self._backend.check(item_key, item.limit, item.window, now, cost=resolved_cost)
            if not result.allowed:
                headers = rate_limit_headers(result, effective_ietf) if effective_include else {}
                exc = RateLimitExceeded(retry_after=result.retry_after or 0.0, headers=headers)
                if self._on_breach:
                    response_obj = self._on_breach(request, exc)
                    if isinstance(response_obj, Response):
                        response.headers.update(response_obj.headers)
                        response.status_code = response_obj.status_code
                        response.body = response_obj.body
                    return None
                raise exc
            if merged is None:
                merged = result
            else:
                merged = RateLimitResult(
                    allowed=True,
                    remaining=min(merged.remaining, result.remaining),
                    limit=max(merged.limit, result.limit),
                    reset_at=max(merged.reset_at, result.reset_at),
                )
        return merged
