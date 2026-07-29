<div align="center">
    <h1>⚡ fastapi-sliding-window</h1>
    <a href="https://pypi.org/project/fastapi-sliding-window/">
        <img alt="PyPI version" src="https://img.shields.io/pypi/v/fastapi-sliding-window?color=blue">
    </a>
    <a href="https://github.com/drawiks/fastapi-sliding-window/actions/workflows/ci.yml">
        <img alt="CI/CD" src="https://github.com/drawiks/fastapi-sliding-window/actions/workflows/ci.yml/badge.svg">
    </a>
    <a href="https://pypi.org/project/fastapi-sliding-window/">
        <img alt="PyPI downloads" src="https://img.shields.io/pypi/dm/fastapi-sliding-window?color=blue">
    </a>
    <img height="20" alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10+-blue">
    <img height="20" alt="License MIT" src="https://img.shields.io/badge/license-MIT-green">
    <img height="20" alt="Status" src="https://img.shields.io/badge/status-stable-brightgreen">
    <a href="https://github.com/drawiks/fastapi-sliding-window">
        <img alt="Ruff" src="https://img.shields.io/badge/code%20style-ruff-000000">
    </a>
    <p><strong>fastapi-sliding-window</strong> — sliding window rate limiter for FastAPI</p>
    <blockquote>(─‿‿─)</blockquote>
</div>

---

```
    ____           __              _ 
   / __/___ ______/ /_____ _____  (_)
  / /_/ __ `/ ___/ __/ __ `/ __ \/ / 
 / __/ /_/ (__  ) /_/ /_/ / /_/ / /  
/_/  \__,_/____/\__/\__,_/ .___/_/   
                        /_/          
         ___     ___                         _           __             
   _____/ (_)___/ (_)___  ____ _   _      __(_)___  ____/ /___ _      __
  / ___/ / / __  / / __ \/ __ `/  | | /| / / / __ \/ __  / __ \ | /| / /
 (__  ) / / /_/ / / / / / /_/ /   | |/ |/ / / / / / /_/ / /_/ / |/ |/ / 
/____/_/_/\__,_/_/_/ /_/\__, /    |__/|__/_/_/ /_/\__,_/\____/|__/|__/  
                       /____/                                           
```

## **📦 installation**

```bash
pip install fastapi-sliding-window
pip install fastapi-sliding-window[redis]  # with Redis support
pip install "fastapi-sliding-window[redis]" uvicorn  # to run examples/
```

> Full working examples are in the [`examples/`](examples/) directory.

---

## **📑 quick start**

### Decorator API (recommended)

```python
from fastapi import FastAPI
from fastapi_sliding_window import Limiter, InMemoryBackend

app = FastAPI()
limiter = Limiter(backend=InMemoryBackend())

@app.get("/login")
@limiter.limit("5/minute")
async def login():
    return {"status": "ok"}
```

### Dependency API

```python
from fastapi import Depends
from fastapi_sliding_window import RateLimit

@app.get("/login", dependencies=[Depends(RateLimit(requests=5, window_seconds=60))])
async def login():
    return {"status": "ok"}
```

---

## **🧩 features**

- 🎯 **5 algorithms** — Sliding Window Log, Sliding Window Counter, Fixed Window, Token Bucket, GCRA
- 💾 **in-memory & Redis** — no external deps for single-node, Redis for distributed
- 🔧 **three usage styles** — `@limiter.limit()` decorator, `Depends(RateLimit(...))`, `RateLimitMiddleware`
- 📝 **standard & IETF headers** — `X-RateLimit-*` or `RateLimit-*` — configurable
- 🚧 **circuit breaker** — `RedisWithFallbackBackend` falls back to in-memory on Redis failure
- ✅ **fully typed** — `py.typed` marker included
- 🚀 **async-native** — thread-safe with `asyncio.Lock`

---

## **⚖️ comparison with alternatives**

| Feature | fastapi-sliding-window | slowapi | fastapi-limiter |
|---------|:---------------------:|:-------:|:---------------:|
| Algorithms | **5** (Fixed, Sliding Log, Sliding Counter, Token Bucket, GCRA) | 2 (Fixed + Sliding) | 1 (Fixed) |
| In-memory backend | ✅ **zero deps** | ✅ (via `limits` lib) | ❌ Redis only |
| Redis backend | ✅ | ✅ | ✅ |
| Circuit Breaker | ✅ | ❌ | ❌ |
| Middleware | ✅ | ✅ | ❌ |
| Dependency | ✅ | ✅ | ✅ |
| Decorator API | ✅ | ✅ | ❌ |
| IETF Headers (`RateLimit-*`) | ✅ | ❌ | ❌ |
| Cost per request | ✅ | ❌ | ❌ |
| Burst support | ✅ | ❌ | ❌ |
| Thread-safe | ✅ | ❌ | ❌ |
| WebSocket | ❌ | ❌ | ✅ |
| memcached | ❌ | ✅ | ❌ |
| mypy strict | ✅ | ❌ | ❌ |
| Python versions | 3.10+ | 3.7+ | 3.9+ |
| External deps (basic mode) | **zero** | `flask-limiter` + `limits` | `pyrate-limiter` |

Each library has its own strengths — choose what fits your use case.

---

## **📖 usage**

### Limiter (decorator API)

```python
from fastapi_sliding_window import Limiter, InMemoryBackend

limiter = Limiter(
    backend=InMemoryBackend(),
    default_limits=["1000/hour"],       # global defaults
    include_headers=True,
    use_ietf_headers=False,              # set True for RateLimit-* headers
    on_breach=lambda req, exc: ...,      # custom 429 handler
)

@app.get("/api")
@limiter.limit("10/minute")              # 10/min + 1000/hour inherited
async def api():
    return {"ok": True}

@app.get("/expensive")
@limiter.limit("5/minute", cost=5)       # each request costs 5 tokens
async def expensive():
    return {"ok": True}

@app.get("/health")
@limiter.exempt                          # no rate limit
async def health():
    return {"ok": True}

@app.get("/internal")
@limiter.limit("10/minute", exempt_when=lambda r: r.headers.get("X-Internal") == "true")
async def internal():
    return {"ok": True}
```

### Depends (per-route, standalone)

```python
from fastapi import Depends
from fastapi_sliding_window import RateLimit, Algorithm

@app.get("/api/data", dependencies=[
    Depends(RateLimit(requests=100, window_seconds=60))
])
async def get_data():
    return {"data": "..."}

@app.post("/api/upload", dependencies=[
    Depends(RateLimit(requests=10, window_seconds=60, algorithm=Algorithm.FIXED_WINDOW))
])
async def upload():
    return {"status": "uploaded"}

async def user_key(request):
    return request.headers.get("X-User-ID", "anonymous")

@app.get("/api/profile", dependencies=[
    Depends(RateLimit(requests=50, window_seconds=60, key_func=user_key))
])
async def profile():
    return {"user": "..."}
```

### Depends (with Limiter delegation)

```python
limiter = Limiter(backend=InMemoryBackend(), default_limits=["1000/hour"])

@app.get("/api", dependencies=[Depends(RateLimit(limiter=limiter))])
@limiter.limit("10/minute")              # endpoint rules + limiter defaults
async def api():
    return {"ok": True}
```

### Middleware (global)

```python
from fastapi_sliding_window import RateLimitMiddleware, Algorithm

app.add_middleware(
    RateLimitMiddleware,
    requests=100,
    window_seconds=60.0,
    algorithm=Algorithm.SLIDING_WINDOW_LOG,
    exclude_paths=["/health"],
)
```

### Middleware (with Limiter delegation)

```python
from fastapi_sliding_window import Limiter, InMemoryBackend, RateLimitMiddleware

limiter = Limiter(backend=InMemoryBackend(), default_limits=["1000/hour"])
app.add_middleware(RateLimitMiddleware, limiter=limiter)
```

### Redis backend

```python
from fastapi_sliding_window import Limiter
from fastapi_sliding_window._utils import from_url

limiter = Limiter(backend=from_url("redis://localhost:6379/0"))
```

### Redis with circuit breaker fallback

```python
from fastapi_sliding_window._backends.fallback import RedisWithFallbackBackend

backend = RedisWithFallbackBackend(
    redis_url="redis://localhost:6379/0",
    failure_threshold=5,       # open circuit after 5 failures
    recovery_timeout=30.0,     # try again after 30s
)
limiter = Limiter(backend=backend)
```

### Burst (Token Bucket / GCRA)

```python
@limiter.limit("5/s burst 10")    # 5 req/s sustained, burst up to 10
async def bursty():
    return {"ok": True}
```

### String-based limits

```python
parse("100/hour")          # RateLimitItem(limit=100, window=3600, unit='hour')
parse("5/s")               # RateLimitItem(limit=5, window=1, unit='s')
parse_many("100/hour;10/minute")  # list[RateLimitItem, RateLimitItem]
```

### Custom cost

```python
@limiter.limit("100/hour", cost=5)                     # fixed cost
@limiter.limit("100/hour", cost=lambda r: 5 if r.method == "POST" else 1)
```

---

## **📊 algorithms**

| Algorithm | Accuracy | Memory | Speed | Best for |
|-----------|----------|--------|-------|----------|
| **Sliding Window Log** | 100% | O(requests/window) | O(1) amortized | accuracy-critical |
| **Sliding Window Counter** | ~99% | O(1) per key | O(1) | high-traffic APIs |
| **Fixed Window** | ~50% (boundary burst) | O(1) per key | O(1) | simple quotas |
| **Token Bucket** | exact | O(1) per key | O(1) | bursty workloads |
| **GCRA** | exact | O(1) per key | O(1) | burst + smooth |

### Sliding Window Log

Stores a timestamp for every request. Prunes entries outside the window on each check. Perfectly accurate, memory grows linearly with request volume within the window.

### Sliding Window Counter

Maintains two counters (current and previous window) and computes a weighted average. Near-accurate with constant memory.

### Fixed Window

Simple counter per time bucket. Suffers from boundary burst (clients can send 2x the limit across a window boundary).

### Token Bucket

Maintains a token count that refills at a fixed rate. Allows bursting up to the bucket capacity. When tokens are exhausted, requests are denied until tokens refill.

### GCRA (Generic Cell Rate Algorithm)

Tracks the next allowed timestamp (TAT). Supports smooth traffic shaping with burst tolerance. O(1) memory per key.

---

## **📊 benchmark results**

### Pure backend speed (100k direct calls)

| Algorithm | checks/s | avg µs |
|-----------|---------:|-------:|
| Fixed Window | 200,700 | 5.0 |
| Sliding Window Log | 199,000 | 5.0 |
| Sliding Window Counter | 142,800 | 7.0 |
| Token Bucket | 189,100 | 5.3 |
| GCRA | 207,300 | 4.8 |

All algorithms complete a check in **5–7 µs** — the overhead is negligible for any real application.

### Full-stack throughput (50 concurrent clients)

Through `RateLimitMiddleware` (pure ASGI, no serialization) + FastAPI.

| Algorithm | RPS | vs baseline |
|-----------|----:|:-----------:|
| Baseline (no limit) | 72,850 | — |
| Fixed Window | 67,660 | 93% |
| Sliding Window Log | 67,320 | 92% |
| Sliding Window Counter | 67,040 | 92% |
| Token Bucket | 67,320 | 92% |
| GCRA | 67,370 | 92% |

Overhead of the rate-limit middleware is **~7–8%** at scale.

### Accuracy (limit 10/s, 50 requests at 10ms intervals)

| Algorithm | Allowed | Blocked | Notes |
|-----------|--------:|--------:|-------|
| Fixed Window | 10 | 40 | |
| Sliding Window Log | 10 | 40 | |
| Sliding Window Counter | 10 | 40 | |
| Token Bucket | 15 | 35 | 5 extra allowed (burst by design) |
| GCRA | 15 | 35 | 5 extra allowed (burst by design) |

> Full benchmark script and methodology: [`benchmarks/`](benchmarks/).

---

## **📝 HTTP headers**

### Standard (default)

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | maximum requests allowed |
| `X-RateLimit-Remaining` | requests remaining in window |
| `X-RateLimit-Reset` | unix timestamp when window resets |
| `Retry-After` | seconds until next request is allowed (429 only) |

### IETF (set `use_ietf_headers=True`)

| Header | Description |
|--------|-------------|
| `RateLimit-Limit` | maximum requests allowed |
| `RateLimit-Remaining` | requests remaining in window |
| `RateLimit-Reset` | unix timestamp when window resets |
| `Retry-After` | seconds until next request is allowed (429 only) |

---

## **🔗 API Reference**

### `Limiter(backend, key_func, default_limits, on_breach, include_headers, use_ietf_headers)`

Main class — decorator API.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `backend` | `RateLimitBackend` | required | storage backend |
| `key_func` | `KeyFunc` | IP-based | client key function |
| `default_limits` | `list[str]` | `None` | global rate limits |
| `on_breach` | `Callable` | `None` | custom 429 handler |
| `include_headers` | `bool` | `True` | add rate limit headers |
| `use_ietf_headers` | `bool` | `False` | use `RateLimit-*` instead of `X-RateLimit-*` |

Methods:
- `@limiter.limit("100/hour", cost=1, key_func=None, exempt_when=None)` — decorator
- `@limiter.exempt` — skip rate limiting
- `await limiter.check(request, response, items)` — programmatic check

### `RateLimit(requests, window_seconds, algorithm, key_func, include_headers, detail, backend, cost, limiter, use_ietf_headers)`

FastAPI dependency for per-route rate limiting.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `requests` | `int | str` | `100` | limit or string like `"100/hour"` |
| `window_seconds` | `float` | `60.0` | window duration |
| `algorithm` | `Algorithm` | `SLIDING_WINDOW_LOG` | algorithm |
| `key_func` | `KeyFunc` | IP-based | client key function |
| `include_headers` | `bool` | `True` | add headers |
| `detail` | `str` | `"Rate limit exceeded"` | 429 detail message |
| `backend` | `RateLimitBackend` | `None` | custom backend |
| `cost` | `int` | `1` | token cost per request |
| `limiter` | `Limiter` | `None` | delegate to Limiter |
| `use_ietf_headers` | `bool` | `False` | IETF headers |

### `RateLimitMiddleware(app, requests, window_seconds, algorithm, key_func, include_headers, exclude_paths, detail, backend, cost, limiter, use_ietf_headers)`

Starlette middleware for global rate limiting.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `requests` | `int | str` | `100` | limit or string like `"100/hour"` |
| `window_seconds` | `float` | `60.0` | window duration |
| `algorithm` | `Algorithm` | `SLIDING_WINDOW_LOG` | algorithm |
| `key_func` | `KeyFunc` | IP-based | client key function |
| `include_headers` | `bool` | `True` | add headers |
| `exclude_paths` | `list[str]` | `None` | paths to skip |
| `detail` | `str` | `"Rate limit exceeded"` | 429 detail |
| `backend` | `RateLimitBackend` | `None` | custom backend |
| `cost` | `int` | `1` | token cost per request |
| `limiter` | `Limiter` | `None` | delegate to Limiter |
| `use_ietf_headers` | `bool` | `False` | IETF headers |

### `Algorithm` enum

`SLIDING_WINDOW_LOG`, `SLIDING_WINDOW_COUNTER`, `FIXED_WINDOW`, `TOKEN_BUCKET`, `GCRA`

### `from_url(url)`

Factory: `"memory://"` → `InMemoryBackend`, `"redis://..."` → `RedisBackend`

### Utility functions

- `parse("100/hour")` → `RateLimitItem`
- `parse_many("100/hour;10/minute")` → `list[RateLimitItem]`
- `rate_limit_headers(result, use_ietf=False)` → `dict[str, str]`

---

## **📜 license**
[MIT](https://github.com/drawiks/fastapi-sliding-window/blob/main/LICENSE)
