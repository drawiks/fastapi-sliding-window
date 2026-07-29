"""Benchmark all rate-limiting algorithms for throughput and accuracy.

Usage:
    python benchmarks/bench.py [--backend] [--throughput] [--accuracy]
"""

from __future__ import annotations

import asyncio
import statistics
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI

from fastapi_sliding_window import (
    Algorithm,
    InMemoryBackend,
    RateLimitMiddleware,
)

ALGORITHMS: list[tuple[str, Algorithm]] = [
    ("Fixed Window", Algorithm.FIXED_WINDOW),
    ("Sliding Window Log", Algorithm.SLIDING_WINDOW_LOG),
    ("Sliding Window Counter", Algorithm.SLIDING_WINDOW_COUNTER),
    ("Token Bucket", Algorithm.TOKEN_BUCKET),
    ("GCRA", Algorithm.GCRA),
]

RATES = [1, 10, 50]
REQUESTS = 2000


def make_middleware_app(name: str, algo: Algorithm, limit: str = "10000/s") -> FastAPI:
    app = FastAPI()

    @app.get("/test")
    async def handler():
        return {"ok": True}

    app.add_middleware(
        RateLimitMiddleware,
        requests=limit,
        algorithm=algo,
        include_headers=True,
    )
    return app


async def run_benchmark(transport: httpx.ASGITransport, n: int, concurrency: int) -> dict:
    latencies: list[float] = []

    async with httpx.AsyncClient(transport=transport, base_url="http://bench") as client:

        async def single() -> int:
            start = time.perf_counter()
            r = await client.get("/test")
            elapsed = time.perf_counter() - start
            latencies.append(elapsed * 1000)
            return r.status_code

        sem = asyncio.Semaphore(concurrency)

        async def worker() -> int:
            async with sem:
                return await single()

        statuses = await asyncio.gather(*[worker() for _ in range(n)])

    ok = sum(1 for s in statuses if s == 200)
    errors = sum(1 for s in statuses if s != 200)
    latencies.sort()
    total_time = sum(latencies) / 1000 / concurrency if latencies else 1

    return {
        "rps": n / total_time if total_time > 0 else 0,
        "latency_avg": statistics.mean(latencies) if latencies else 0,
        "latency_p50": latencies[len(latencies) // 2] if latencies else 0,
        "latency_p95": latencies[int(len(latencies) * 0.95)] if latencies else 0,
        "latency_p99": latencies[int(len(latencies) * 0.99)] if latencies else 0,
        "ok": ok,
        "errors": errors,
    }


async def bench_throughput():
    print("=" * 100)
    print(
        f"{'Algorithm':<25} {'Clients':>8} {'RPS':>10} {'Avg ms':>8} {'p50 ms':>8} {'p95 ms':>8} {'p99 ms':>8} {'Errors':>8}"
    )
    print("=" * 100)

    for concurrency in RATES:
        # baseline — no middleware
        app = FastAPI()

        @app.get("/test")
        async def handler():
            return {"ok": True}

        base = await run_benchmark(
            httpx.ASGITransport(app=app, client=("127.0.0.1", 8000)),
            REQUESTS,
            concurrency,
        )
        print(
            f"{'Baseline (no limit)':<25} {concurrency:>8} {base['rps']:>10.0f} "
            f"{base['latency_avg']:>8.2f} {base['latency_p50']:>8.2f} "
            f"{base['latency_p95']:>8.2f} {base['latency_p99']:>8.2f} "
            f"{base['errors']:>8}"
        )

        for name, algo in ALGORITHMS:
            app = make_middleware_app(name, algo)
            res = await run_benchmark(
                httpx.ASGITransport(app=app, client=("127.0.0.1", 8000)),
                REQUESTS,
                concurrency,
            )
            print(
                f"{name:<25} {concurrency:>8} {res['rps']:>10.0f} "
                f"{res['latency_avg']:>8.2f} {res['latency_p50']:>8.2f} "
                f"{res['latency_p95']:>8.2f} {res['latency_p99']:>8.2f} "
                f"{res['errors']:>8}"
            )
        print()


async def bench_accuracy():
    print("=" * 90)
    print("Accuracy test — limit 10/s, fire 50 requests (100ms apart)")
    print("=" * 90)
    print(f"{'Algorithm':<25} {'allowed':>8} {'blocked':>8} {'1st Retry-After':>16}")
    print("-" * 90)

    for name, algo in ALGORITHMS:
        app = make_middleware_app(name, algo, "10/s")

        transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 8000))
        async with httpx.AsyncClient(transport=transport, base_url="http://bench") as client:
            results = []
            for _ in range(50):
                results.append(await client.get("/test"))
                await asyncio.sleep(0.01)  # 10ms interval

            allowed = sum(1 for r in results if r.status_code == 200)
            blocked = sum(1 for r in results if r.status_code == 429)
            retry_after = ""
            for r in results:
                if r.status_code == 429:
                    retry_after = r.headers.get("retry-after", "?")
                    break

            print(f"{name:<25} {allowed:>8} {blocked:>8} {retry_after:>16}")


async def bench_pure_backend():
    print("=" * 70)
    print("Pure backend speed — 100000 direct check() calls")
    print("=" * 70)
    print(f"{'Algorithm':<25} {'checks/s':>10} {'avg µs':>8}")
    print("-" * 70)
    N = 100_000

    for name, algo in ALGORITHMS:
        backend = InMemoryBackend(algorithm=algo)
        key = "bench"
        now = time.monotonic()

        start = time.perf_counter()
        for i in range(N):
            await backend.check(key, 1000000, 1, now + (i / 1000))
        elapsed = time.perf_counter() - start

        checks_per_sec = N / elapsed
        avg_us = (elapsed / N) * 1_000_000
        print(f"{name:<25} {checks_per_sec:>10.0f} {avg_us:>8.1f}")


async def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", action="store_true")
    parser.add_argument("--throughput", action="store_true")
    parser.add_argument("--accuracy", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if not any(vars(args).values()):
        args.all = True

    if args.all or args.backend:
        await bench_pure_backend()
        print()

    if args.all or args.throughput:
        await bench_throughput()

    if args.all or args.accuracy:
        await bench_accuracy()


if __name__ == "__main__":
    asyncio.run(main())
