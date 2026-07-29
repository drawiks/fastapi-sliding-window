"""Basic decorator API with in-memory backend.

Usage:
    # Terminal 1: start the server
    python examples/01_basic_decorator.py

    # Terminal 2: test rate limiting
    for i in $(seq 1 8); do
        curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/login
    done
    # First 5 requests return 200, then 429.
"""

import uvicorn
from fastapi import FastAPI

from fastapi_sliding_window import InMemoryBackend, Limiter

app = FastAPI()
limiter = Limiter(backend=InMemoryBackend())


@app.get("/login")
@limiter.limit("5/minute")
async def login():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
