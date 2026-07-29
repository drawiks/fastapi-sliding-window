"""Multiple limits — combine global defaults with per-endpoint limits.

The Limiter has default_limits ("1000/hour"). The endpoint adds
"10/minute" on top. Both limits are enforced independently.

Usage:
    python examples/11_multiple_limits.py

    # Fast requests hit 10/minute limit first
    for i in $(seq 1 15); do
        curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/
    done
"""

import uvicorn
from fastapi import FastAPI

from fastapi_sliding_window import InMemoryBackend, Limiter

app = FastAPI()
limiter = Limiter(backend=InMemoryBackend(), default_limits=["1000/hour"])


@app.get("/")
@limiter.limit("10/minute")
async def root():
    return {"message": "Dual-limited endpoint"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
