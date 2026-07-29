"""Dependency API — per-route rate limiting via Depends(RateLimit(...)).

Usage:
    python examples/02_dependency_api.py

    curl http://localhost:8000/
    # Repeat 12+ times — after 10 requests within 60s you get 429.
"""

import uvicorn
from fastapi import Depends, FastAPI

from fastapi_sliding_window import RateLimit

app = FastAPI()


@app.get("/", dependencies=[Depends(RateLimit(requests=10, window_seconds=60))])
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
