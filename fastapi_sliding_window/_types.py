from __future__ import annotations

from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.requests import Request


class Algorithm(str, Enum):
    SLIDING_WINDOW_LOG = "sliding_window_log"
    SLIDING_WINDOW_COUNTER = "sliding_window_counter"
    FIXED_WINDOW = "fixed_window"
    GCRA = "gcra"
    TOKEN_BUCKET = "token_bucket"


KeyFunc = Callable[["Request"], Awaitable[str] | str]
