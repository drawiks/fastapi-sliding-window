"""Custom key function — rate-limit by user ID or API key instead of IP.

Usage:
    python examples/08_custom_key_func.py

    # Rate-limited per X-User-Id value
    curl -H "X-User-Id: alice" http://localhost:8000/
    curl -H "X-User-Id: bob"   http://localhost:8000/
    # alice gets 429 after 3 requests, bob can still go.
"""

import uvicorn
from fastapi import FastAPI, Request

from fastapi_sliding_window import InMemoryBackend, Limiter


async def user_key(request: Request) -> str:
    return request.headers.get("X-User-Id", "anonymous")


app = FastAPI()
limiter = Limiter(backend=InMemoryBackend(), key_func=user_key)


@app.get("/")
@limiter.limit("3/minute")
async def root():
    return {"message": "User-based rate limiting"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
