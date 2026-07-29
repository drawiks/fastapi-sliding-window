"""Limiter delegation — combining Limiter with Dependency and Middleware.

The Limiter holds default_limits. Both RateLimit (dependency) and
RateLimitMiddleware can delegate to the same Limiter, enforcing
default limits + endpoint-specific rules.

Usage:
    python examples/04_limiter_delegation.py

    curl http://localhost:8000/          # limited by middleware (5/10s)
    curl http://localhost:8000/profile   # limited by middleware + @limiter.limit
"""

import uvicorn
from fastapi import Depends, FastAPI

from fastapi_sliding_window import InMemoryBackend, Limiter, RateLimit, RateLimitMiddleware

limiter = Limiter(backend=InMemoryBackend(), default_limits=["1000/hour"])

app = FastAPI()
app.add_middleware(RateLimitMiddleware, limiter=limiter, requests=5, window_seconds=10)


@app.get("/", dependencies=[Depends(RateLimit(limiter=limiter))])
async def root():
    return {"message": "Hello World"}


@app.get("/profile", dependencies=[Depends(RateLimit(limiter=limiter))])
@limiter.limit("2/minute")
async def profile():
    return {"user": "alice"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
