from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    limit: int
    reset_at: float
    retry_after: float | None = None


class RateLimitBackend(ABC):
    @abstractmethod
    async def check(self, key: str, limit: int, window: float, now: float) -> RateLimitResult: ...

    @abstractmethod
    async def reset(self, key: str) -> None: ...
