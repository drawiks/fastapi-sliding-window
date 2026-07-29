from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fastapi_sliding_window._backends.redis import RedisBackend


@pytest.fixture
def mock_redis():
    with patch("fastapi_sliding_window._backends.redis._Redis", MagicMock()):
        yield


@pytest.fixture
async def backend(mock_redis):
    b = RedisBackend("redis://localhost:6379/0", algorithm="sliding_window_log")
    fake_redis = AsyncMock()
    fake_redis.register_script = MagicMock(return_value=AsyncMock())
    b._redis = fake_redis
    b._scripts = {
        "fixed_window": fake_redis.register_script(),
        "sliding_window_log": fake_redis.register_script(),
        "sliding_window_counter": fake_redis.register_script(),
        "gcra": fake_redis.register_script(),
    }
    yield b


async def _run(backend, algo, key, limit, window, now, cost=1, **kwargs):
    backend._algorithm = algo
    script = backend._scripts[algo]
    script.return_value = (
        kwargs.get("allowed", 1),
        kwargs.get("remaining", limit - 1),
        kwargs.get("reset_at", now + window),
        kwargs.get("retry_after", -1),
    )
    return await backend.check(key, limit, window, now, cost=cost)


async def test_redis_allows_within_limit(backend):
    result = await _run(backend, "sliding_window_log", "key", 3, 10.0, 100.0)
    assert result.allowed is True
    assert result.remaining == 2


async def test_redis_blocks_after_limit(backend):
    result = await _run(backend, "sliding_window_log", "key", 3, 10.0, 100.0, allowed=0, remaining=0)
    assert result.allowed is False
    assert result.remaining == 0


async def test_redis_window_expiry(backend):
    result = await _run(backend, "sliding_window_log", "key", 3, 5.0, 105.0)
    assert result.allowed is True


async def test_redis_reset(backend):
    await _run(backend, "sliding_window_log", "key", 3, 10.0, 100.0)
    await backend.reset("key")
    result = await _run(backend, "sliding_window_log", "key", 3, 10.0, 100.0)
    assert result.allowed is True


async def test_redis_different_keys(backend):
    result_a = await _run(backend, "sliding_window_log", "a", 3, 10.0, 100.0, allowed=0, remaining=0)
    assert result_a.allowed is False
    result_b = await _run(backend, "sliding_window_log", "b", 3, 10.0, 100.0)
    assert result_b.allowed is True


async def test_redis_reset_at(backend):
    result = await _run(backend, "sliding_window_log", "key", 5, 60.0, 100.0, reset_at=160.0)
    assert result.reset_at == 160.0


async def test_redis_limit_zero(backend):
    result = await backend.check("key", 0, 10.0, 100.0)
    assert result.allowed is False
    assert result.remaining == 0
    assert result.limit == 0


async def test_redis_retry_after_in_response(backend):
    result = await _run(backend, "sliding_window_log", "key", 3, 10.0, 100.0, allowed=0, remaining=0, retry_after=4.5)
    assert result.allowed is False
    assert result.retry_after == 4.5


async def test_all_algorithms_execute_lua(mock_redis):
    for algo in ["fixed_window", "sliding_window_log", "sliding_window_counter", "gcra"]:
        b = RedisBackend("redis://localhost:6379/0", algorithm=algo)
        fake_redis = AsyncMock()
        fake_redis.register_script = MagicMock(return_value=AsyncMock(return_value=(1, 9, 110.0, -1)))
        b._redis = fake_redis
        b._scripts = {
            name: fake_redis.register_script()
            for name in ["fixed_window", "sliding_window_log", "sliding_window_counter", "gcra"]
        }
        result = await b.check("k", 10, 10.0, 100.0, cost=1)
        assert result.allowed is True
        assert result.remaining == 9


async def test_fixed_window_script_called(backend):
    await _run(backend, "fixed_window", "key", 3, 10.0, 100.0)
    script = backend._scripts["fixed_window"]
    script.assert_awaited_once()


async def test_sliding_window_log_script_includes_uuid(backend):
    backend._algorithm = "sliding_window_log"
    script = backend._scripts["sliding_window_log"]
    script.return_value = (1, 9, 110.0, -1)
    await backend.check("key", 10, 10.0, 100.0)
    args = script.await_args.kwargs["args"]
    uid_arg = args[4]
    assert ":" in uid_arg


async def test_token_bucket_script_includes_uuid(backend):
    backend._scripts["token_bucket"] = backend._scripts["sliding_window_log"]
    backend._algorithm = "token_bucket"
    script = backend._scripts["token_bucket"]
    script.return_value = (1, 9, 110.0, -1)
    await backend.check("key", 10, 10.0, 100.0)
    args = script.await_args.kwargs["args"]
    uid_arg = args[5]
    assert ":" in uid_arg


async def test_http_headers_in_result(backend):
    result = await _run(backend, "sliding_window_log", "key", 10, 60.0, 100.0, remaining=8)
    assert result.limit == 10
    assert result.remaining == 8


async def test_retry_after_none_when_allowed(backend):
    result = await _run(backend, "sliding_window_log", "key", 10, 60.0, 100.0)
    assert result.retry_after is None


async def test_redis_raises_without_redis_lib():
    with patch("fastapi_sliding_window._backends.redis._Redis", None):
        b = RedisBackend("redis://localhost:6379/0")
        with pytest.raises(RuntimeError, match="redis library is not installed"):
            await b.check("key", 10, 60.0, 100.0)
