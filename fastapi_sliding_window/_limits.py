from __future__ import annotations

import re
from dataclasses import dataclass

UNITS: dict[str, float] = {
    "second": 1,
    "seconds": 1,
    "sec": 1,
    "secs": 1,
    "s": 1,
    "minute": 60,
    "minutes": 60,
    "min": 60,
    "mins": 60,
    "m": 60,
    "hour": 3600,
    "hours": 3600,
    "hr": 3600,
    "hrs": 3600,
    "h": 3600,
    "day": 86400,
    "days": 86400,
    "d": 86400,
    "week": 604800,
    "weeks": 604800,
    "wk": 604800,
    "wks": 604800,
    "w": 604800,
}

RATE_RE = re.compile(
    r"\s*(\d+)\s*"
    r"(?:/\s*([a-z]+)"
    r"|\s+per\s+([a-z]+))"
    r"(?:\s+burst\s+(\d+))?"
    r"\s*",
    re.IGNORECASE,
)

SEP_RE = re.compile(r"\s*[;,|]\s*")


@dataclass(frozen=True)
class RateLimitItem:
    limit: int
    window: float
    unit: str
    burst: int | None = None

    def __post_init__(self) -> None:
        if self.window <= 0:
            raise ValueError(f"window must be positive, got {self.window}")
        if self.limit <= 0:
            raise ValueError(f"limit must be positive, got {self.limit}")
        if self.burst is not None and self.burst < 0:
            raise ValueError(f"burst must be non-negative, got {self.burst}")


def parse(s: str) -> RateLimitItem:
    m = RATE_RE.fullmatch(s.strip())
    if not m:
        raise ValueError(f"Invalid rate limit string: {s!r}")
    limit = int(m.group(1))
    unit_str = (m.group(2) or m.group(3)).lower()
    window = UNITS.get(unit_str)
    if window is None:
        raise ValueError(f"Unknown unit: {unit_str!r}")
    burst: int | None = int(m.group(4)) if m.group(4) else None
    if burst == 0:
        burst = None
    return RateLimitItem(limit, window, unit_str, burst)


def parse_many(s: str) -> list[RateLimitItem]:
    stripped = s.strip()
    if not stripped:
        return []
    return [parse(part) for part in SEP_RE.split(stripped)]
