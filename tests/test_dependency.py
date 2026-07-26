from __future__ import annotations

import pytest
from fastapi import FastAPI, Depends
from starlette.testclient import TestClient

from fastapi_rate_limit import Algorithm, RateLimit


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
