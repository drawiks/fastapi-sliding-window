from __future__ import annotations

import pytest
from fastapi import FastAPI, Depends
from starlette.testclient import TestClient

from fastapi_sliding_window import Algorithm, RateLimit


async def async_key(request) -> str:
    return "async-key"


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()

    @app.get("/test", dependencies=[Depends(RateLimit(requests=3, window_seconds=60.0))])
    async def test_endpoint():
        return {"status": "ok"}

    @app.get("/fixed", dependencies=[Depends(RateLimit(requests=2, window_seconds=60.0, algorithm=Algorithm.FIXED_WINDOW))])
    async def fixed_endpoint():
        return {"status": "ok"}

    @app.get("/counter", dependencies=[Depends(RateLimit(requests=2, window_seconds=60.0, algorithm=Algorithm.SLIDING_WINDOW_COUNTER))])
    async def counter_endpoint():
        return {"status": "ok"}

    @app.get("/custom-key", dependencies=[Depends(RateLimit(requests=2, window_seconds=60.0, key_func=lambda r: "constant"))])
    async def custom_key_endpoint():
        return {"status": "ok"}

    @app.get("/no-headers", dependencies=[Depends(RateLimit(requests=1, window_seconds=60.0, include_headers=False))])
    async def no_headers_endpoint():
        return {"status": "ok"}

    @app.get("/custom-detail", dependencies=[Depends(RateLimit(requests=1, window_seconds=60.0, detail="Custom error"))])
    async def custom_detail_endpoint():
        return {"status": "ok"}

    @app.get("/async-key", dependencies=[Depends(RateLimit(requests=2, window_seconds=60.0, key_func=async_key))])
    async def async_key_endpoint():
        return {"status": "ok"}

    return app


class TestDependency:
    def test_allows_requests_within_limit(self, app: FastAPI) -> None:
        client = TestClient(app)

        for _ in range(3):
            response = client.get("/test")
            assert response.status_code == 200

    def test_blocks_after_limit(self, app: FastAPI) -> None:
        client = TestClient(app)

        for _ in range(3):
            client.get("/test")

        response = client.get("/test")
        assert response.status_code == 429

    def test_headers_on_success(self, app: FastAPI) -> None:
        client = TestClient(app)
        response = client.get("/test")

        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_rate_limited_returns_429(self, app: FastAPI) -> None:
        client = TestClient(app)
        for _ in range(3):
            client.get("/test")

        response = client.get("/test")
        assert response.status_code == 429
        assert response.json()["detail"] == "Rate limit exceeded"

    def test_fixed_window_algorithm(self, app: FastAPI) -> None:
        client = TestClient(app)
        for _ in range(2):
            response = client.get("/fixed")
            assert response.status_code == 200

        response = client.get("/fixed")
        assert response.status_code == 429

    def test_sliding_window_counter_algorithm(self, app: FastAPI) -> None:
        client = TestClient(app)
        for _ in range(2):
            response = client.get("/counter")
            assert response.status_code == 200

        response = client.get("/counter")
        assert response.status_code == 429

    def test_custom_key_func(self, app: FastAPI) -> None:
        client = TestClient(app)
        for _ in range(2):
            response = client.get("/custom-key")
            assert response.status_code == 200

        response = client.get("/custom-key")
        assert response.status_code == 429

    def test_different_endpoints_independent(self, app: FastAPI) -> None:
        client = TestClient(app)
        for _ in range(3):
            client.get("/test")

        response = client.get("/fixed")
        assert response.status_code == 200

    def test_include_headers_false_omits_headers(self, app: FastAPI) -> None:
        client = TestClient(app)
        response = client.get("/no-headers")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" not in response.headers

    def test_custom_detail_in_429_response(self, app: FastAPI) -> None:
        client = TestClient(app)
        client.get("/custom-detail")
        response = client.get("/custom-detail")
        assert response.status_code == 429
        assert response.json()["detail"] == "Custom error"

    def test_async_key_func(self, app: FastAPI) -> None:
        client = TestClient(app)
        response = client.get("/async-key")
        assert response.status_code == 200

        response = client.get("/async-key")
        assert response.status_code == 200

        response = client.get("/async-key")
        assert response.status_code == 429

    def test_429_includes_rate_limit_headers(self, app: FastAPI) -> None:
        client = TestClient(app)
        for _ in range(3):
            client.get("/test")
        response = client.get("/test")
        assert response.status_code == 429
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "3"
