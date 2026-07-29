"""Redis with circuit breaker — falls back to in-memory when Redis is down.

Usage:
    # Start without Redis — the circuit breaker will detect the failure
    # after `failure_threshold` requests and switch to in-memory fallback.
    python examples/06_circuit_breaker.py

    # In another terminal:
    for i in $(seq 1 20); do
        curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/
    done
"""

import uvicorn
from fastapi import FastAPI

from fastapi_sliding_window import Limiter
from fastapi_sliding_window._backends.fallback import RedisWithFallbackBackend

backend = RedisWithFallbackBackend(
    redis_url="redis://localhost:6379/0",
    failure_threshold=3,
    recovery_timeout=30.0,
)

app = FastAPI()
limiter = Limiter(backend=backend)


@app.get("/")
@limiter.limit("5/minute")
async def root():
    return {"message": "Circuit breaker active"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
