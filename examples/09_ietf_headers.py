"""IETF standard headers — use RateLimit-* headers instead of X-RateLimit-*.

Shows both formats for comparison.

Usage:
    python examples/09_ietf_headers.py

    # Standard headers (default)
    curl -v http://localhost:8000/standard 2>&1 | grep -i rate-limit

    # IETF headers
    curl -v http://localhost:8000/ietf 2>&1 | grep -i rate-limit
"""

import uvicorn
from fastapi import Depends, FastAPI

from fastapi_sliding_window import RateLimit

app = FastAPI()


@app.get(
    "/standard",
    dependencies=[Depends(RateLimit(requests=5, window_seconds=60, use_ietf_headers=False))],
)
async def standard():
    return {"headers": "X-RateLimit-*"}


@app.get(
    "/ietf",
    dependencies=[Depends(RateLimit(requests=5, window_seconds=60, use_ietf_headers=True))],
)
async def ietf():
    return {"headers": "RateLimit-* (IETF)"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
