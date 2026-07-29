from __future__ import annotations

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from fastapi_sliding_window import Algorithm, Limiter, RateLimitMiddleware
from fastapi_sliding_window._backends.memory import InMemoryBackend


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    return app


class TestMiddleware:
    def test_allows_requests_within_limit(self, app: FastAPI) -> None:
        app.add_middleware(RateLimitMiddleware, requests=5, window_seconds=60.0)
        client = TestClient(app)

        for _ in range(5):
            response = client.get("/test")
            assert response.status_code == 200

    def test_blocks_after_limit(self, app: FastAPI) -> None:
        app.add_middleware(RateLimitMiddleware, requests=3, window_seconds=60.0)
        client = TestClient(app)

        for _ in range(3):
            response = client.get("/test")
            assert response.status_code == 200

        response = client.get("/test")
        assert response.status_code == 429

    def test_headers_present(self, app: FastAPI) -> None:
        app.add_middleware(RateLimitMiddleware, requests=5, window_seconds=60.0)
        client = TestClient(app)

        response = client.get("/test")
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "5"
        assert response.headers["X-RateLimit-Remaining"] == "4"

    def test_exclude_paths(self, app: FastAPI) -> None:
        app.add_middleware(
            RateLimitMiddleware,
            requests=1,
            window_seconds=60.0,
            exclude_paths=["/test"],
        )
        client = TestClient(app)

        for _ in range(5):
            response = client.get("/test")
            assert response.status_code == 200

    def test_custom_key_func(self, app: FastAPI) -> None:
        def custom_key(request):
            return "fixed-key"

        app.add_middleware(RateLimitMiddleware, requests=2, window_seconds=60.0, key_func=custom_key)
        client = TestClient(app)

        response = client.get("/test")
        assert response.status_code == 200

        response = client.get("/test")
        assert response.status_code == 200

        response = client.get("/test")
        assert response.status_code == 429

    def test_429_headers_include_all_fields(self, app: FastAPI) -> None:
        app.add_middleware(RateLimitMiddleware, requests=2, window_seconds=60.0)
        client = TestClient(app)
        client.get("/test")
        client.get("/test")
        response = client.get("/test")
        assert response.status_code == 429
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_retry_after_in_429(self, app: FastAPI) -> None:
        app.add_middleware(RateLimitMiddleware, requests=1, window_seconds=60.0)
        client = TestClient(app)
        client.get("/test")
        response = client.get("/test")
        assert response.status_code == 429
        assert "Retry-After" in response.headers

    def test_include_headers_false(self, app: FastAPI) -> None:
        app.add_middleware(RateLimitMiddleware, requests=1, window_seconds=60.0, include_headers=False)
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" not in response.headers

    def test_custom_detail(self, app: FastAPI) -> None:
        app.add_middleware(RateLimitMiddleware, requests=1, window_seconds=60.0, detail="Custom error")
        client = TestClient(app)
        client.get("/test")
        response = client.get("/test")
        assert response.status_code == 429
        assert response.json()["detail"] == "Custom error"

    def test_fixed_window_algorithm(self, app: FastAPI) -> None:
        app.add_middleware(
            RateLimitMiddleware,
            requests=2,
            window_seconds=60.0,
            algorithm=Algorithm.FIXED_WINDOW,
        )
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
        response = client.get("/test")
        assert response.status_code == 200
        response = client.get("/test")
        assert response.status_code == 429

    def test_cost_int(self, app: FastAPI) -> None:
        app.add_middleware(RateLimitMiddleware, requests=2, window_seconds=60.0, cost=2)
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
        response = client.get("/test")
        assert response.status_code == 429

    def test_requests_as_string(self, app: FastAPI) -> None:
        app.add_middleware(RateLimitMiddleware, requests="5/hour")
        client = TestClient(app)
        for _ in range(5):
            response = client.get("/test")
            assert response.status_code == 200
        response = client.get("/test")
        assert response.status_code == 429

    def test_use_ietf_headers(self, app: FastAPI) -> None:
        app.add_middleware(RateLimitMiddleware, requests=3, window_seconds=60.0, use_ietf_headers=True)
        client = TestClient(app)
        response = client.get("/test")
        assert "RateLimit-Limit" in response.headers
        assert "X-RateLimit-Limit" not in response.headers

    def test_sliding_window_counter_algorithm(self, app: FastAPI) -> None:
        app.add_middleware(
            RateLimitMiddleware,
            requests=2,
            window_seconds=60.0,
            algorithm=Algorithm.SLIDING_WINDOW_COUNTER,
        )
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
        response = client.get("/test")
        assert response.status_code == 200
        response = client.get("/test")
        assert response.status_code == 429

    def test_exempt_when_skips_rate_limit(self, app: FastAPI) -> None:
        app.add_middleware(
            RateLimitMiddleware,
            requests=1,
            window_seconds=60.0,
            exempt_when=lambda r: r.headers.get("X-Skip") == "yes",
        )
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
        response = client.get("/test")
        assert response.status_code == 429
        response = client.get("/test", headers={"X-Skip": "yes"})
        assert response.status_code == 200

    def test_exempt_when_allows_within_limit(self, app: FastAPI) -> None:
        app.add_middleware(
            RateLimitMiddleware,
            requests=3,
            window_seconds=60.0,
            exempt_when=lambda r: r.headers.get("X-Skip") == "yes",
        )
        client = TestClient(app)
        for _ in range(4):
            response = client.get("/test", headers={"X-Skip": "yes"})
            assert response.status_code == 200

    def test_exempt_when_limiter_mode(self) -> None:
        backend = InMemoryBackend()
        limiter = Limiter(backend=backend, default_limits=["1/sec"])
        app = FastAPI()

        @app.get("/test")
        async def endpoint() -> dict:
            return {"ok": True}

        app.add_middleware(
            RateLimitMiddleware,
            limiter=limiter,
            exempt_when=lambda r: r.headers.get("X-Skip") == "yes",
        )
        client = TestClient(app)
        response = client.get("/test", headers={"X-Skip": "yes"})
        assert response.status_code == 200
        response = client.get("/test", headers={"X-Skip": "yes"})
        assert response.status_code == 200


class TestMiddlewareLimiterDelegation:
    def test_middleware_with_limiter_allows(self) -> None:
        backend = InMemoryBackend()
        limiter = Limiter(backend=backend)
        app = FastAPI()

        @app.get("/test")
        async def endpoint() -> dict:
            return {"ok": True}

        app.add_middleware(RateLimitMiddleware, limiter=limiter)
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

    def test_middleware_with_limiter_default_limits_blocks(self) -> None:
        backend = InMemoryBackend()
        limiter = Limiter(backend=backend, default_limits=["1/sec"])
        app = FastAPI()

        @app.get("/test")
        async def endpoint() -> dict:
            return {"ok": True}

        app.add_middleware(RateLimitMiddleware, limiter=limiter)
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
        response = client.get("/test")
        assert response.status_code == 429
