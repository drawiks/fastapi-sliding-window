# Benchmark Results

Generated on 2026-07-29 with Python 3.12 / Linux on an AMD64 machine.

## Pure Backend Speed

100,000 direct `backend.check()` calls (algorithm only, no HTTP overhead).

| Algorithm | checks/s | avg µs |
|-----------|---------:|-------:|
| Fixed Window | 200,700 | 5.0 |
| Sliding Window Log | 199,000 | 5.0 |
| Sliding Window Counter | 142,800 | 7.0 |
| Token Bucket | 189,100 | 5.3 |
| GCRA | 207,300 | 4.8 |

All algorithms complete a rate-limit check in **5–7 µs**.

## Full-Stack Throughput

Through `RateLimitMiddleware` (pure ASGI) + FastAPI + ASGITransport (2000 requests per run).

| Algorithm | Clients=1 | Clients=10 | Clients=50 |
|-----------|----------:|-----------:|-----------:|
| Baseline (no limit) | 1,457 | 14,580 | 72,850 |
| Fixed Window | 1,346 | 13,606 | 67,660 |
| Sliding Window Log | 1,347 | 13,556 | 67,320 |
| Sliding Window Counter | 1,319 | 13,500 | 67,040 |
| Token Bucket | 1,336 | 13,459 | 67,320 |
| GCRA | 1,355 | 13,510 | 67,370 |

Overhead of rate-limit middleware: **~7%** at 50 concurrent clients. The middleware is a pure ASGI implementation — no request serialization.

## Accuracy

Limit: 10/s. 50 sequential requests with 10ms interval.

| Algorithm | Allowed | Blocked | Expected |
|-----------|--------:|--------:|----------|
| Fixed Window | 10 | 40 | ✅ |
| Sliding Window Log | 10 | 40 | ✅ |
| Sliding Window Counter | 10 | 40 | ✅ |
| Token Bucket | 15 | 35 | ✅ (burst=10) |
| GCRA | 15 | 35 | ✅ (burst=10) |

- Fixed Window, Sliding Window Log, and Sliding Window Counter reject exactly 40 of 50 requests.
- Token Bucket and GCRA allow 5 extra requests due to built-in burst capacity (`burst=limit`), which is by design.
