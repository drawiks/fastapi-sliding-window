from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi_sliding_window._backends.base import RateLimitBackend, RateLimitResult

try:
    from redis.asyncio import Redis as _Redis
except ImportError:
    _Redis = None

LUA_SCRIPTS: dict[str, str] = {
    "fixed_window": """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local cost = tonumber(ARGV[4])
        local window_start = math.floor(now / window) * window
        local window_key = key .. ":" .. window_start
        local count = redis.call("INCRBY", window_key, cost)
        if count == cost then
            redis.call("PEXPIRE", window_key, window * 1000)
        end
        local remaining = math.max(0, limit - count)
        local reset_at = window_start + window
        local allowed = count <= limit
        local retry_after = -1
        if not allowed then
            retry_after = reset_at - now
        end
        return {allowed and 1 or 0, remaining, reset_at, retry_after}
    """,
    "sliding_window_log": """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local cost = tonumber(ARGV[4])
        local uuid = ARGV[5]
        redis.call("ZREMRANGEBYSCORE", key, 0, now - window)
        local count = redis.call("ZCARD", key)
        if count + cost > limit then
            local oldest = redis.call("ZRANGE", key, 0, 0, "WITHSCORES")
            local retry_after = tonumber(oldest[2]) + window - now
            return {0, 0, now + window, retry_after}
        end
        for i = 1, cost do
            redis.call("ZADD", key, now, uuid .. ":" .. i)
        end
        redis.call("PEXPIRE", key, window * 2000)
        local remaining = limit - count - cost
        return {1, remaining, now + window, -1}
    """,
    "sliding_window_counter": """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local cost = tonumber(ARGV[4])
        local window_start = math.floor(now / window) * window
        local curr_key = key .. ":curr:" .. window_start
        local prev_key = key .. ":prev:" .. window_start
        local curr_count = redis.call("GET", curr_key) or 0
        local prev_count = redis.call("GET", prev_key) or 0
        if type(curr_count) == "table" then curr_count = 0 end
        if type(prev_count) == "table" then prev_count = 0 end
        curr_count = tonumber(curr_count)
        prev_count = tonumber(prev_count)
        local overlap = (window_start + window - now) / window
        local weighted = prev_count * overlap + curr_count
        if weighted + cost <= limit then
            local new_count = redis.call("INCRBY", curr_key, cost)
            if new_count == cost then
                redis.call("PEXPIRE", curr_key, window * 2000)
            end
            local new_weighted = weighted + cost
            local remaining = math.max(0, math.floor(limit - new_weighted))
            local reset_at = window_start + window
            return {1, remaining, reset_at, -1}
        end
        local reset_at = window_start + window
        local retry_after = reset_at - now
        return {0, 0, reset_at, retry_after}
    """,
    "gcra": """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local burst = tonumber(ARGV[4])
        local cost = tonumber(ARGV[5])
        local T = window / limit
        local tau = (burst - 1) * T
        local tat = redis.call("GET", key)
        if not tat then
            tat = 0
        else
            tat = tonumber(tat)
        end
        if tat <= now then
            local new_tat = now + cost * T
            local ttl = math.ceil((burst / limit * window + 1) * 1000)
            redis.call("SET", key, new_tat, "PX", ttl)
            local remaining = math.max(0, burst - cost)
            return {1, remaining, now + window, -1}
        end
        local delay = tat - now
        if delay <= tau then
            local new_tat = tat + cost * T
            local ttl = math.ceil((burst / limit * window + 1) * 1000)
            redis.call("SET", key, new_tat, "PX", ttl)
            local remaining = math.max(0, math.floor((tau - delay) / T))
            return {1, remaining, now + window, -1}
        end
        local retry_after = delay - tau
        return {0, 0, now + window, retry_after}
    """,
}


class RedisBackend(RateLimitBackend):
    def __init__(
        self,
        url: str,
        algorithm: str = "sliding_window_log",
        key_prefix: str = "rl:",
        burst: int | None = None,
    ) -> None:
        self._url = url
        self._algorithm = algorithm
        self._prefix = key_prefix
        self._burst = burst
        self._redis: _Redis | None = None
        self._scripts: dict[str, Any] = {}

    async def _ensure_redis(self) -> _Redis:
        if _Redis is None:
            raise RuntimeError(
                "redis library is not installed. Install with: pip install fastapi-sliding-window[redis]"
            )
        if self._redis is None:
            self._redis = _Redis.from_url(self._url, decode_responses=True)
            for name, src in LUA_SCRIPTS.items():
                self._scripts[name] = self._redis.register_script(src)
        return self._redis

    async def check(self, key: str, limit: int, window: float, now: float, cost: int = 1) -> RateLimitResult:
        if limit <= 0:
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=limit,
                reset_at=now + window,
                retry_after=0.0,
            )
        await self._ensure_redis()
        script = self._scripts[self._algorithm]
        burst = self._burst or limit
        member = f"{now}:{uuid4().hex}"
        if self._algorithm == "fixed_window":
            args = [str(limit), str(window), str(now), str(cost)]
        elif self._algorithm == "sliding_window_log":
            args = [str(limit), str(window), str(now), str(cost), member]
        elif self._algorithm == "sliding_window_counter":
            args = [str(limit), str(window), str(now), str(cost)]
        elif self._algorithm == "gcra":
            args = [str(limit), str(window), str(now), str(burst), str(cost)]
        else:
            args = [str(limit), str(window), str(now), str(burst), str(cost), member]
        keys = [f"{self._prefix}{{{key}}}"]
        allowed_raw, remaining_raw, reset_at_raw, retry_after_raw = await script(keys=keys, args=args)
        retry_after: float | None = None
        if retry_after_raw >= 0:
            retry_after = float(retry_after_raw)
        return RateLimitResult(
            allowed=bool(allowed_raw),
            remaining=int(remaining_raw),
            limit=limit,
            reset_at=float(reset_at_raw),
            retry_after=retry_after,
        )

    async def reset(self, key: str) -> None:
        r = await self._ensure_redis()
        await r.delete(f"{self._prefix}{{{key}}}")
