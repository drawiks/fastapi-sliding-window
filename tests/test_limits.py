from __future__ import annotations

import pytest

from fastapi_sliding_window._limits import RateLimitItem, parse, parse_many


class TestParse:
    def test_parse_simple(self) -> None:
        item = parse("100/hour")
        assert item.limit == 100
        assert item.window == 3600
        assert item.unit == "hour"
        assert item.burst is None

    def test_parse_per_minute(self) -> None:
        item = parse("10/minute")
        assert item.limit == 10
        assert item.window == 60
        assert item.unit == "minute"

    def test_parse_per_second(self) -> None:
        item = parse("5/sec")
        assert item.limit == 5
        assert item.window == 1
        assert item.unit == "sec"

    def test_parse_per_day(self) -> None:
        item = parse("1000/day")
        assert item.limit == 1000
        assert item.window == 86400
        assert item.unit == "day"

    def test_parse_per_week(self) -> None:
        item = parse("50/week")
        assert item.limit == 50
        assert item.window == 604800
        assert item.unit == "week"

    def test_parse_with_burst(self) -> None:
        item = parse("5/s burst 10")
        assert item.limit == 5
        assert item.window == 1
        assert item.unit == "s"
        assert item.burst == 10

    def test_parse_without_slash(self) -> None:
        item = parse("100 per hour")
        assert item.limit == 100
        assert item.window == 3600

    def test_parse_case_insensitive(self) -> None:
        item = parse("100/Hour")
        assert item.limit == 100
        assert item.window == 3600

    def test_parse_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid rate limit string"):
            parse("invalid")

    def test_parse_unknown_unit_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown unit"):
            parse("100/decade")

    def test_parse_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid rate limit string"):
            parse("")


class TestParseMany:
    def test_parse_many_semicolon(self) -> None:
        items = parse_many("100/hour;10/minute")
        assert len(items) == 2
        assert items[0].limit == 100 and items[0].unit == "hour"
        assert items[1].limit == 10 and items[1].unit == "minute"

    def test_parse_many_comma(self) -> None:
        items = parse_many("5/s, 10/min")
        assert len(items) == 2

    def test_parse_many_pipe(self) -> None:
        items = parse_many("3/s | 5/min")
        assert len(items) == 2

    def test_parse_many_single(self) -> None:
        items = parse_many("100/hour")
        assert len(items) == 1

    def test_parse_many_empty(self) -> None:
        items = parse_many("")
        assert items == []


class TestRateLimitItem:
    def test_dataclass(self) -> None:
        item = RateLimitItem(limit=10, window=60, unit="minute", burst=20)
        assert item.limit == 10
        assert item.window == 60
        assert item.unit == "minute"
        assert item.burst == 20

    def test_default_burst_none(self) -> None:
        item = RateLimitItem(limit=10, window=60, unit="minute")
        assert item.burst is None

    def test_immutable(self) -> None:
        item = RateLimitItem(limit=10, window=60, unit="minute")
        with pytest.raises(AttributeError):
            item.limit = 20  # type: ignore[misc]
