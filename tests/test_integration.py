from __future__ import annotations

from fastapi import Depends, FastAPI
from starlette.testclient import TestClient

from fastapi_sliding_window import Algorithm, Limiter, RateLimit, RateLimitMiddleware
from fastapi_sliding_window._backends.memory import InMemoryBackend


def test_middleware_blocks_with_limiter_and_default_limits() -> None:
    backend = InMemoryBackend()
    limiter = Limiter(backend=backend, default_limits=["2/sec"])
    app = FastAPI()

    @app.get("/test")
    async def endpoint() -> dict:
        return {"ok": True}

    app.add_middleware(RateLimitMiddleware, limiter=limiter)
    client = TestClient(app)

    response = client.get("/test")
    assert response.status_code == 200
    response = client.get("/test")
    assert response.status_code == 200
    response = client.get("/test")
    assert response.status_code == 429


def test_dependency_blocks_after_limit() -> None:
    app = FastAPI()

    @app.get("/test", dependencies=[Depends(RateLimit(requests=2, window_seconds=60.0))])
    async def endpoint() -> dict:
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/test")
    assert response.status_code == 200
    response = client.get("/test")
    assert response.status_code == 200
    response = client.get("/test")
    assert response.status_code == 429


def test_dependency_with_limiter_and_decorator() -> None:
    backend = InMemoryBackend()
    limiter = Limiter(backend=backend, default_limits=["5/minute"])
    app = FastAPI()

    @app.get("/test", dependencies=[Depends(RateLimit(limiter=limiter))])
    @limiter.limit("2/minute")
    async def endpoint() -> dict:
        return {"ok": True}

    client = TestClient(app)

    for _ in range(2):
        response = client.get("/test")
        assert response.status_code == 200

    response = client.get("/test")
    assert response.status_code == 429


def test_dependency_exempt_when_skips() -> None:
    app = FastAPI()

    @app.get(
        "/test",
        dependencies=[
            Depends(
                RateLimit(
                    requests=1,
                    window_seconds=60.0,
                    exempt_when=lambda r: r.headers.get("X-Skip") == "yes",
                )
            )
        ],
    )
    async def endpoint() -> dict:
        return {"ok": True}

    client = TestClient(app)

    response = client.get("/test")
    assert response.status_code == 200

    response = client.get("/test")
    assert response.status_code == 429

    response = client.get("/test", headers={"X-Skip": "yes"})
    assert response.status_code == 200


def test_middleware_with_dependency_independent_counters() -> None:
    mw_backend = InMemoryBackend()
    dep_backend = InMemoryBackend()
    app = FastAPI()

    @app.get("/a")
    async def endpoint_a() -> dict:
        return {"ok": True}

    @app.get("/b", dependencies=[Depends(RateLimit(requests=2, window_seconds=60.0, backend=dep_backend))])
    async def endpoint_b() -> dict:
        return {"ok": True}

    app.add_middleware(RateLimitMiddleware, requests=3, window_seconds=60.0, backend=mw_backend)
    client = TestClient(app)

    response = client.get("/a")
    assert response.status_code == 200
    response = client.get("/b")
    assert response.status_code == 200
    response = client.get("/b")
    assert response.status_code == 200


def test_headers_from_middleware_and_dependency() -> None:
    app = FastAPI()

    @app.get("/dep", dependencies=[Depends(RateLimit(requests=2, window_seconds=60.0))])
    async def dep_endpoint() -> dict:
        return {"ok": True}

    @app.get("/mw")
    async def mw_endpoint() -> dict:
        return {"ok": True}

    app.add_middleware(RateLimitMiddleware, requests=2, window_seconds=60.0)
    client = TestClient(app)

    response = client.get("/dep")
    assert response.status_code == 200
    assert "X-RateLimit-Remaining" in response.headers
    remaining = response.headers["X-RateLimit-Remaining"]
    assert remaining in ("1, 1", "1")

    response = client.get("/mw")
    assert response.status_code == 200
    assert "X-RateLimit-Remaining" in response.headers
    assert "0" in response.headers["X-RateLimit-Remaining"]


def test_all_algorithms_work_with_middleware() -> None:
    for algo in Algorithm:
        app = FastAPI()

        @app.get("/test")
        async def endpoint() -> dict:
            return {"ok": True}

        app.add_middleware(
            RateLimitMiddleware,
            requests=1,
            window_seconds=60.0,
            algorithm=algo,
        )
        client = TestClient(app)

        response = client.get("/test")
        assert response.status_code == 200, f"{algo} failed"

        response = client.get("/test")
        assert response.status_code == 429, f"{algo} failed to block"


def test_middleware_exclude_paths_with_dependency() -> None:
    app = FastAPI()

    @app.get("/public", dependencies=[Depends(RateLimit(requests=1, window_seconds=60.0))])
    async def public() -> dict:
        return {"ok": True}

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True}

    app.add_middleware(
        RateLimitMiddleware,
        requests=5,
        window_seconds=60.0,
        exclude_paths=["/health"],
    )
    client = TestClient(app)

    for _ in range(10):
        response = client.get("/health")
        assert response.status_code == 200

    response = client.get("/public")
    assert response.status_code == 200


def test_string_limit_in_middleware_and_dependency() -> None:
    app = FastAPI()

    @app.get("/test", dependencies=[Depends(RateLimit(requests="2/minute"))])
    async def endpoint() -> dict:
        return {"ok": True}

    app.add_middleware(RateLimitMiddleware, requests="5/minute")
    client = TestClient(app)

    response = client.get("/test")
    assert response.status_code == 200


def test_cost_parameter_in_middleware() -> None:
    app = FastAPI()

    @app.get("/test")
    async def endpoint() -> dict:
        return {"ok": True}

    app.add_middleware(RateLimitMiddleware, requests=4, window_seconds=60.0, cost=2)
    client = TestClient(app)

    response = client.get("/test")
    assert response.status_code == 200

    response = client.get("/test")
    assert response.status_code == 200

    response = client.get("/test")
    assert response.status_code == 429


def test_different_backends_independent() -> None:
    dep_backend = InMemoryBackend()
    mw_backend = InMemoryBackend()

    app = FastAPI()

    @app.get("/test", dependencies=[Depends(RateLimit(requests=1, window_seconds=60.0, backend=dep_backend))])
    async def endpoint() -> dict:
        return {"ok": True}

    app.add_middleware(RateLimitMiddleware, requests=3, window_seconds=60.0, backend=mw_backend)
    client = TestClient(app)

    response = client.get("/test")
    assert response.status_code == 200

    response = client.get("/test")
    assert response.status_code == 429

    response = client.get("/test")
    assert response.status_code == 429
