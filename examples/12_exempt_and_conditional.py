"""Exempt and conditional rate limiting.

Shows:
  - @limiter.exempt — skip rate limiting entirely
  - exempt_when — conditionally skip based on request properties

Usage:
    python examples/12_exempt_and_conditional.py

    curl http://localhost:8000/health          # always 200 (exempt)
    curl http://localhost:8000/internal         # 200 with header, 429 without
    curl -H "X-Internal: true" http://localhost:8000/internal
"""

import uvicorn
from fastapi import FastAPI

from fastapi_sliding_window import InMemoryBackend, Limiter

app = FastAPI()
limiter = Limiter(backend=InMemoryBackend())


@app.get("/health")
@limiter.exempt
async def health():
    return {"status": "healthy"}


@app.get("/internal")
@limiter.limit("3/minute", exempt_when=lambda r: r.headers.get("X-Internal") == "true")
async def internal():
    return {"message": "internal endpoint"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
