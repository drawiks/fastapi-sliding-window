<div align="center">
    <h1>⚡ fastapi-sliding-window</h1>
    <a href="https://pypi.org/project/fastapi-sliding-window/">
        <img alt="PyPI version" src="https://img.shields.io/pypi/v/fastapi-sliding-window?color=blue">
    </a>
    <img height="20" alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10+-blue">
    <img height="20" alt="License MIT" src="https://img.shields.io/badge/license-MIT-green">
    <img height="20" alt="Status" src="https://img.shields.io/badge/status-stable-brightgreen">
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
```

---

## **📑 quick start**

```python
from fastapi import FastAPI, Depends
from fastapi_sliding_window import RateLimit

app = FastAPI()

@app.get("/login", dependencies=[Depends(RateLimit(requests=5, window_seconds=60))])
async def login():
    return {"status": "ok"}
```

---

## **🧩 features**

- 🎯 **3 algorithms** — Sliding Window Log (exact), Sliding Window Counter (O(1) memory), Fixed Window
- 💾 **in-memory** — no Redis required, zero external dependencies
- 🔧 **two usage styles** — `Depends(RateLimit(...))` per-route or `RateLimitMiddleware` globally
- 📝 **standard headers** — `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`
- ✅ **fully typed** — `py.typed` marker included
- 🚀 **async-native** — built on `asyncio.Lock` for thread safety

---

## **📖 usage**

### Depends (per-route)

```python
from fastapi import Depends
from fastapi_sliding_window import RateLimit, Algorithm

# Sliding Window Log (default, most accurate)
@app.get("/api/data", dependencies=[
    Depends(RateLimit(requests=100, window_seconds=60))
])
async def get_data():
    return {"data": "..."}

# Fixed Window (fastest, O(1) memory)
@app.post("/api/upload", dependencies=[
    Depends(RateLimit(requests=10, window_seconds=60, algorithm=Algorithm.FIXED_WINDOW))
])
async def upload():
    return {"status": "uploaded"}

# custom key function (per-user instead of per-IP)
async def user_key(request):
    return request.headers.get("X-User-ID", "anonymous")

@app.get("/api/profile", dependencies=[
    Depends(RateLimit(requests=50, window_seconds=60, key_func=user_key))
])
async def profile():
    return {"user": "..."}
```

### Middleware (global)

```python
from fastapi_sliding_window import RateLimitMiddleware, Algorithm

app.add_middleware(
    RateLimitMiddleware,
    requests=100,
    window_seconds=60.0,
    algorithm=Algorithm.SLIDING_WINDOW_LOG,
    exclude_paths=["/health"],  # skip rate limiting for these paths
)
```

---

## **📊 algorithms**

| Algorithm | Accuracy | Memory | Speed | Best for |
|-----------|----------|--------|-------|----------|
| **Sliding Window Log** | 100% | O(requests/window) | O(1) amortized | accuracy-critical endpoints |
| **Sliding Window Counter** | ~99% | O(1) per key | O(1) | high-traffic APIs |
| **Fixed Window** | ~50% (boundary burst) | O(1) per key | O(1) | simple quotas |

### Sliding Window Log

Stores a timestamp for every request. Prunes entries outside the window on each check. Perfectly accurate, memory grows linearly with request volume within the window.

### Sliding Window Counter

Maintains two counters (current and previous window) and computes a weighted average. Near-accurate with constant memory. Best balance of accuracy and performance.

### Fixed Window

Simple counter per time bucket. Suffers from boundary burst (clients can send 2x the limit across a window boundary).

---

## **📝 HTTP headers**

successful responses include:

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | maximum requests allowed |
| `X-RateLimit-Remaining` | requests remaining in window |
| `X-RateLimit-Reset` | unix timestamp when window resets |
| `Retry-After` | seconds until next request is allowed (429, middleware only) |

---

## **🔗 API Reference**

### `RateLimit(requests, window_seconds, algorithm, key_func, include_headers)`

FastAPI dependency for per-route rate limiting.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `requests` | `int` | required | max requests per window |
| `window_seconds` | `float` | required | window duration in seconds |
| `algorithm` | `Algorithm` | `SLIDING_WINDOW_LOG` | rate limiting algorithm |
| `key_func` | `KeyFunc` | IP-based | function to extract client key |
| `include_headers` | `bool` | `True` | add rate limit headers |

### `RateLimitMiddleware(requests, window_seconds, algorithm, key_func, include_headers, exclude_paths)`

Starlette middleware for global rate limiting.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `requests` | `int` | `100` | max requests per window |
| `window_seconds` | `float` | `60.0` | window duration in seconds |
| `algorithm` | `Algorithm` | `SLIDING_WINDOW_LOG` | rate limiting algorithm |
| `key_func` | `KeyFunc` | IP-based | function to extract client key |
| `include_headers` | `bool` | `True` | add rate limit headers |
| `exclude_paths` | `list[str]` | `None` | paths to skip rate limiting |

---

## **📜 license**
[MIT](https://github.com/drawiks/fastapi-sliding-window/blob/main/LICENSE)
