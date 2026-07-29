"""Burst and cost — Token Bucket burst capacity and variable cost per request.

Shows:
  - burst syntax: "5/s burst 10" allows 5 sustained, bursts up to 10
  - fixed cost: each request consumes N tokens
  - dynamic cost: cost depends on request (e.g., method or body)

Usage:
    python examples/07_burst_and_cost.py

    # Burst: rapid requests consume burst capacity
    curl http://localhost:8000/burst
    curl http://localhost:8000/burst  # repeat quickly

    # Cost: POST costs 5 tokens, GET costs 1
    curl -X POST http://localhost:8000/cost
    curl http://localhost:8000/cost
"""

import uvicorn
from fastapi import FastAPI, Request

from fastapi_sliding_window import InMemoryBackend, Limiter

app = FastAPI()
limiter = Limiter(backend=InMemoryBackend())


@app.get("/burst")
@limiter.limit("5/s burst 10")
async def burst():
    return {"message": "burst endpoint"}


@app.route("/cost", methods=["GET", "POST"])
@limiter.limit("100/hour", cost=lambda r: 5 if r.method == "POST" else 1)
async def cost(request: Request):
    return {"method": request.method, "cost": 5 if request.method == "POST" else 1}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
