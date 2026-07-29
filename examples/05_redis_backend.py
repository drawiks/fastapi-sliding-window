"""Redis backend — distributed rate limiting across multiple workers.

Requires a running Redis server. Install redis extra first:
    pip install fastapi-sliding-window[redis]

Usage:
    # Terminal 1 (ensure Redis is running on localhost:6379)
    python examples/05_redis_backend.py

    # Terminal 2
    for i in $(seq 1 12); do
        curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/
    done
"""

import uvicorn
from fastapi import FastAPI

from fastapi_sliding_window import Limiter
from fastapi_sliding_window._utils import from_url

app = FastAPI()

backend = from_url("redis://localhost:6379/0")
limiter = Limiter(backend=backend)


@app.get("/")
@limiter.limit("10/minute")
async def root():
    return {"message": "Hello from Redis-backed rate limiter"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
