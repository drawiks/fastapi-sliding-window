"""Algorithm comparison — all 5 algorithms on separate endpoints.

Each endpoint allows 5 requests per 10 seconds using a different algorithm.
Compare behavior at window boundaries.

Usage:
    python examples/10_algorithm_comparison.py

    # Rapid-fire test
    for algo in fixed sliding_log sliding_counter token_bucket gcra; do
        echo "=== $algo ==="
        for i in $(seq 1 7); do
            curl -s -o /dev/null -w "%{http_code} " http://localhost:8000/$algo
        done
        echo
    done
"""

import uvicorn
from fastapi import FastAPI

from fastapi_sliding_window import Algorithm, RateLimitMiddleware

app = FastAPI()

mw = {
    "algorithm": None,
}

for algo, name in [
    (Algorithm.FIXED_WINDOW, "fixed"),
    (Algorithm.SLIDING_WINDOW_LOG, "sliding_log"),
    (Algorithm.SLIDING_WINDOW_COUNTER, "sliding_counter"),
    (Algorithm.TOKEN_BUCKET, "token_bucket"),
    (Algorithm.GCRA, "gcra"),
]:
    local_app = FastAPI()

    @local_app.get(f"/{name}")
    async def handler(algo=algo):
        return {"algorithm": algo.value}

    app.mount(f"/{name}", local_app)
    app.add_middleware(
        RateLimitMiddleware,
        requests=5,
        window_seconds=10.0,
        algorithm=algo,
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
