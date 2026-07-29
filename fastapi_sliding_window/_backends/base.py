from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    limit: int
    reset_at: float
    retry_after: float | None = None


def _evict_if_needed(data: dict[str, Any], max_keys: int, key: str) -> None:
    if len(data) >= max_keys and key not in data:
        data.pop(next(iter(data)))


class RateLimitBackend(ABC):
    @abstractmethod
    async def check(self, key: str, limit: int, window: float, now: float, cost: int = 1) -> RateLimitResult: ...

    @abstractmethod
    async def reset(self, key: str) -> None: ...
