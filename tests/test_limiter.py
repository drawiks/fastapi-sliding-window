from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from fastapi_sliding_window import Limiter, RateLimitExceeded
from fastapi_sliding_window._backends.memory import InMemoryBackend
from fastapi_sliding_window._limits import RateLimitItem
from fastapi_sliding_window._types import KeyFunc
from fastapi_sliding_window._utils import default_key_func


@pytest.fixture
def backend() -> InMemoryBackend:
    return InMemoryBackend()


@pytest.fixture
def limiter(backend: InMemoryBackend) -> Limiter:
    return Limiter(backend=backend)


class TestLimiterInit:
    def test_default_limits(self) -> None:
        limiter = Limiter(backend=InMemoryBackend(), default_limits=["100/hour"])
        assert len(limiter._default_limits) == 1
        assert limiter._default_limits[0][0].limit == 100

    def test_empty_default_limits(self) -> None:
        limiter = Limiter(backend=InMemoryBackend())
        assert limiter._default_limits == []

    def test_custom_key_func(self) -> None:
        def custom_key(request: Request) -> str:
            return "custom"

        limiter = Limiter(backend=InMemoryBackend(), key_func=custom_key)
        assert limiter._key_func is custom_key

    def test_on_breach(self) -> None:
        def breach_handler(request: Request, exc: RateLimitExceeded) -> Response:
            return JSONResponse({"error": "breach"}, status_code=429)

        limiter = Limiter(backend=InMemoryBackend(), on_breach=breach_handler)
        assert limiter._on_breach is breach_handler

    def test_include_headers_default(self) -> None:
        limiter = Limiter(backend=InMemoryBackend())
        assert limiter._include_headers is True

    def test_use_ietf_headers(self) -> None:
        limiter = Limiter(backend=InMemoryBackend(), use_ietf_headers=True)
        assert limiter._use_ietf is True


class TestLimiterLimit:
    def test_limit_decorator_sets_items(self, limiter: Limiter) -> None:
        @limiter.limit("100/hour")
        def endpoint() -> dict:
            return {"ok": True}

        items = getattr(endpoint, "__rate_limit_items__", [])
        assert len(items) == 1
        assert items[0].limit == 100
        assert items[0].window == 3600

    def test_limit_decorator_multiple(self, limiter: Limiter) -> None:
        @limiter.limit("100/hour")
        @limiter.limit("10/minute")
        def endpoint() -> dict:
            return {"ok": True}

        items = getattr(endpoint, "__rate_limit_items__", [])
        assert len(items) == 2
        assert items[0].limit == 100
        assert items[1].limit == 10

    def test_limit_preserves_endpoint(self, limiter: Limiter) -> None:
        @limiter.limit("5/s")
        def my_endpoint() -> str:
            return "hello"

        assert my_endpoint() == "hello"

    def test_limit_with_burst(self, limiter: Limiter) -> None:
        @limiter.limit("5/s burst 10")
        def endpoint() -> dict:
            return {"ok": True}

        items = getattr(endpoint, "__rate_limit_items__", [])
        assert items[0].burst == 10

    def test_limit_with_exempt_when(self, limiter: Limiter) -> None:
        exempt = lambda r: True  # type: ignore[misc]

        @limiter.limit("10/minute", exempt_when=exempt)
        def endpoint() -> dict:
            return {"ok": True}

        rules = getattr(endpoint, "__rate_limit_rules__", [])
        assert len(rules) == 1
        _, _, _, exempt_when = rules[0]
        assert exempt_when is exempt

    @pytest.mark.asyncio
    async def test_limit_exempt_when_skips_rate_limit(self, limiter: Limiter) -> None:
        @limiter.limit("1/sec", exempt_when=lambda r: True)
        def endpoint() -> dict:
            return {"ok": True}

        rules = getattr(endpoint, "__rate_limit_rules__", [])
        request = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
        response = Response()
        await limiter.check_rules(request, response, rules)
        response2 = Response()
        await limiter.check_rules(request, response2, rules)
        assert response2.status_code == 200

    @pytest.mark.asyncio
    async def test_limit_exempt_when_false_blocks(self, limiter: Limiter) -> None:
        @limiter.limit("1/sec", exempt_when=lambda r: False)
        def endpoint() -> dict:
            return {"ok": True}

        rules = getattr(endpoint, "__rate_limit_rules__", [])
        request = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
        response = Response()
        await limiter.check_rules(request, response, rules)
        response2 = Response()
        with pytest.raises(RateLimitExceeded):
            await limiter.check_rules(request, response2, rules)


class TestLimiterExempt:
    def test_exempt_sets_attribute(self, limiter: Limiter) -> None:
        @limiter.exempt
        def endpoint() -> dict:
            return {"ok": True}

        assert endpoint._rate_limit_exempt is True

    def test_exempt_preserves_function(self, limiter: Limiter) -> None:
        @limiter.exempt
        def health() -> dict:
            return {"status": "ok"}

        assert health() == {"status": "ok"}


class TestLimiterCheck:
    @pytest.mark.asyncio
    async def test_allows_within_limit(self, backend: InMemoryBackend, limiter: Limiter) -> None:
        items = [RateLimitItem(limit=3, window=10.0, unit="second")]
        request = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
        response = Response()
        await limiter.check(request, response, items)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_blocks_after_limit(self, backend: InMemoryBackend, limiter: Limiter) -> None:
        items = [RateLimitItem(limit=1, window=10.0, unit="second")]
        request = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
        response = Response()
        await limiter.check(request, response, items)
        with pytest.raises(RateLimitExceeded):
            await limiter.check(request, response, items)

    @pytest.mark.asyncio
    async def test_includes_headers(self, backend: InMemoryBackend, limiter: Limiter) -> None:
        items = [RateLimitItem(limit=3, window=10.0, unit="second")]
        request = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
        response = Response()
        await limiter.check(request, response, items)
        assert "X-RateLimit-Limit" in response.headers

    @pytest.mark.asyncio
    async def test_omits_headers(self, backend: InMemoryBackend) -> None:
        limiter = Limiter(backend=backend, include_headers=False)
        items = [RateLimitItem(limit=3, window=10.0, unit="second")]
        request = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
        response = Response()
        await limiter.check(request, response, items)
        assert "X-RateLimit-Limit" not in response.headers

    @pytest.mark.asyncio
    async def test_custom_cost(self, backend: InMemoryBackend, limiter: Limiter) -> None:
        items = [RateLimitItem(limit=5, window=60.0, unit="minute")]
        request = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
        response = Response()
        await limiter.check(request, response, items, cost=5)
        with pytest.raises(RateLimitExceeded):
            await limiter.check(request, response, items, cost=5)

    @pytest.mark.asyncio
    async def test_uses_default_limits(self, backend: InMemoryBackend) -> None:
        limiter = Limiter(backend=backend, default_limits=["1/sec"])
        items: list[RateLimitItem] = []
        request = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
        response = Response()
        await limiter.check(request, response, items)
        with pytest.raises(RateLimitExceeded):
            await limiter.check(request, response, items)

    @pytest.mark.asyncio
    async def test_multiple_items_fastest_fail(self, backend: InMemoryBackend, limiter: Limiter) -> None:
        items = [
            RateLimitItem(limit=100, window=3600.0, unit="hour"),
            RateLimitItem(limit=2, window=10.0, unit="second"),
        ]
        request = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
        response = Response()
        await limiter.check(request, response, items)
        await limiter.check(request, response, items)
        with pytest.raises(RateLimitExceeded):
            await limiter.check(request, response, items)

    @pytest.mark.asyncio
    async def test_custom_key_func(self, backend: InMemoryBackend, limiter: Limiter) -> None:
        items = [RateLimitItem(limit=1, window=10.0, unit="second")]
        key_func: KeyFunc = lambda r: "fixed-key"
        request = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
        response = Response()
        await limiter.check(request, response, items, key_func=key_func)
        with pytest.raises(RateLimitExceeded):
            await limiter.check(request, response, items, key_func=key_func)


class TestLimiterCheckRules:
    @pytest.mark.asyncio
    async def test_check_rules_allows_within_limit(self, limiter: Limiter) -> None:
        rules: list[tuple[list[RateLimitItem], int, None, None]] = [
            ([RateLimitItem(limit=3, window=10.0, unit="second")], 1, None, None),
        ]
        request = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
        response = Response()
        await limiter.check_rules(request, response, rules)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_check_rules_blocks_after_limit(self, limiter: Limiter) -> None:
        rules: list[tuple[list[RateLimitItem], int, None, None]] = [
            ([RateLimitItem(limit=1, window=10.0, unit="second")], 1, None, None),
        ]
        request = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
        response = Response()
        await limiter.check_rules(request, response, rules)
        with pytest.raises(RateLimitExceeded):
            await limiter.check_rules(request, response, rules)

    @pytest.mark.asyncio
    async def test_check_rules_multiple_items_fastest_fail(self, limiter: Limiter) -> None:
        rules: list[tuple[list[RateLimitItem], int, None, None]] = [
            (
                [
                    RateLimitItem(limit=100, window=3600.0, unit="hour"),
                    RateLimitItem(limit=2, window=10.0, unit="second"),
                ],
                1,
                None,
                None,
            ),
        ]
        request = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
        response = Response()
        await limiter.check_rules(request, response, rules)
        await limiter.check_rules(request, response, rules)
        with pytest.raises(RateLimitExceeded):
            await limiter.check_rules(request, response, rules)

    @pytest.mark.asyncio
    async def test_check_rules_default_limits(self, backend: InMemoryBackend) -> None:
        limiter = Limiter(backend=backend, default_limits=["1/sec"])
        rules: list[tuple[list[RateLimitItem], int, None, None]] = []
        request = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
        response = Response()
        await limiter.check_rules(request, response, rules)
        with pytest.raises(RateLimitExceeded):
            await limiter.check_rules(request, response, rules)

    @pytest.mark.asyncio
    async def test_check_rules_with_exempt_when(self, limiter: Limiter) -> None:
        rules: list[tuple[list[RateLimitItem], int, None, Callable[[Request], bool]]] = [
            (
                [RateLimitItem(limit=1, window=10.0, unit="second")],
                1,
                None,
                lambda r: True,
            ),
        ]
        request = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
        response = Response()
        await limiter.check_rules(request, response, rules)
        response2 = Response()
        await limiter.check_rules(request, response2, rules)
        assert response2.status_code == 200

    @pytest.mark.asyncio
    async def test_callable_cost(self, backend: InMemoryBackend) -> None:
        limiter = Limiter(backend=backend)
        items = [RateLimitItem(limit=5, window=60.0, unit="minute")]
        callable_cost = MagicMock(return_value=5)
        request = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
        response = Response()
        await limiter.check(request, response, items, cost=callable_cost)
        callable_cost.assert_called_once_with(request)
        with pytest.raises(RateLimitExceeded):
            await limiter.check(request, response, items, cost=callable_cost)

    @pytest.mark.asyncio
    async def test_on_breach_suppresses_exception(self, backend: InMemoryBackend) -> None:
        def breach_handler(request: Request, exc: RateLimitExceeded) -> Response:
            return JSONResponse({"handled": True}, status_code=429)

        limiter = Limiter(backend=backend, on_breach=breach_handler)
        items = [RateLimitItem(limit=1, window=10.0, unit="second")]
        request = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
        response = Response()
        await limiter.check(request, response, items)
        await limiter.check(request, response, items)
        assert response.status_code == 429

    def test_default_key_func_returns_unknown_for_empty_request(self) -> None:
        class FakeRequest:
            client = None

        assert default_key_func(FakeRequest()) == "unknown"  # type: ignore[arg-type]
