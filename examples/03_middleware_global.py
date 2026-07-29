"""Global middleware — applies rate limiting to every route.

Usage:
    python examples/03_middleware_global.py

    # /api and /data share the same global limit
    curl http://localhost:8000/api
    curl http://localhost:8000/data

    # /health is excluded from rate limiting
    curl http://localhost:8000/health
"""

import uvicorn
from fastapi import FastAPI

from fastapi_sliding_window import Algorithm, RateLimitMiddleware

app = FastAPI()

app.add_middleware(
    RateLimitMiddleware,
    requests=5,
    window_seconds=10.0,
    algorithm=Algorithm.SLIDING_WINDOW_LOG,
    exclude_paths=["/health"],
)


@app.get("/api")
async def api():
    return {"endpoint": "api"}


@app.get("/data")
async def data():
    return {"endpoint": "data"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
