from __future__ import annotations

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from fastapi_rate_limit import RateLimitMiddleware


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
        app.add_middleware(RateLimitMiddleware, requests=1, window_seconds=60.0, exclude_paths=["/test"])
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
