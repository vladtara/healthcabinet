"""
Unit tests for login rate limiting logic (app/core/rate_limit.py).

NOTE: These tests use a mock Redis client injected via the `redis` parameter.
The integration between the rate limiter and a live Redis instance is NOT
covered in the CI suite — the login endpoint bypasses rate limiting in
integration tests because Redis is absent and the fail-open design swallows
connection errors silently. See check_login_rate_limit for the fail-open
design rationale.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.core.rate_limit import (
    LOGIN_RATE_LIMIT_ATTEMPTS,
    LOGIN_RATE_LIMIT_IP_ATTEMPTS,
    REFRESH_RATE_LIMIT_IP_ATTEMPTS,
    check_login_rate_limit,
    check_refresh_rate_limit,
    reset_login_rate_limit,
)


def _make_redis(count: int = 1, ttl: int = 45) -> AsyncMock:
    """Return a mock Redis client that simulates Lua eval returning `count`."""
    redis = AsyncMock()
    # eval() replaces incr+expire — returns the post-increment counter atomically
    redis.eval.return_value = count
    redis.ttl.return_value = ttl
    redis.delete.return_value = 1
    return redis


# ── check_login_rate_limit ───────────────────────────────────────────────────


async def test_below_limit_does_not_raise():
    redis = _make_redis(count=1)
    await check_login_rate_limit("user@example.com", redis=redis)
    # eval() called once (Lua script handles INCR+EXPIRE atomically)
    redis.eval.assert_called_once()
    # Third positional arg is the key (script, numkeys, key, window_seconds)
    assert redis.eval.call_args.args[2] == "rate_limit:login:user@example.com"


async def test_at_limit_does_not_raise():
    redis = _make_redis(count=LOGIN_RATE_LIMIT_ATTEMPTS)
    await check_login_rate_limit("user@example.com", redis=redis)


async def test_above_limit_raises_429():
    redis = _make_redis(count=LOGIN_RATE_LIMIT_ATTEMPTS + 1, ttl=30)
    with pytest.raises(HTTPException) as exc_info:
        await check_login_rate_limit("user@example.com", redis=redis)
    assert exc_info.value.status_code == 429
    assert exc_info.value.headers["Retry-After"] == "30"


async def test_retry_after_uses_ttl():
    redis = _make_redis(count=LOGIN_RATE_LIMIT_ATTEMPTS + 1, ttl=55)
    with pytest.raises(HTTPException) as exc_info:
        await check_login_rate_limit("user@example.com", redis=redis)
    assert exc_info.value.headers["Retry-After"] == "55"


async def test_retry_after_minimum_1_when_ttl_zero():
    redis = _make_redis(count=LOGIN_RATE_LIMIT_ATTEMPTS + 1, ttl=0)
    with pytest.raises(HTTPException) as exc_info:
        await check_login_rate_limit("user@example.com", redis=redis)
    assert exc_info.value.headers["Retry-After"] == "1"


async def test_email_key_is_lowercased():
    redis = _make_redis(count=1)
    await check_login_rate_limit("User@EXAMPLE.COM", redis=redis)
    assert redis.eval.call_args.args[2] == "rate_limit:login:user@example.com"


async def test_atomic_incr_expire_uses_lua_eval():
    """INCR+EXPIRE is atomic via Lua eval — no separate redis.incr / redis.expire calls."""
    redis = _make_redis(count=5)
    await check_login_rate_limit("user@example.com", redis=redis)
    redis.eval.assert_called_once()


async def test_ip_key_checked_when_ip_provided():
    redis = _make_redis(count=1)
    await check_login_rate_limit("user@example.com", ip="1.2.3.4", redis=redis)
    # Third positional arg of each eval() call is the key
    keys = [call.args[2] for call in redis.eval.call_args_list]
    assert "rate_limit:login:user@example.com" in keys
    assert "rate_limit:login:ip:1.2.3.4" in keys


async def test_ip_key_not_checked_when_ip_omitted():
    redis = _make_redis(count=1)
    await check_login_rate_limit("user@example.com", redis=redis)
    keys = [call.args[2] for call in redis.eval.call_args_list]
    assert not any("ip:" in key for key in keys)


async def test_ip_limit_raises_429():
    """Per-IP threshold triggers 429 even when per-email count is fine."""
    redis = AsyncMock()
    redis.ttl.return_value = 42

    async def eval_side_effect(script: str, numkeys: int, key: str, window: str) -> int:
        return LOGIN_RATE_LIMIT_IP_ATTEMPTS + 1 if "ip:" in key else 1

    redis.eval.side_effect = eval_side_effect

    with pytest.raises(HTTPException) as exc_info:
        await check_login_rate_limit("user@example.com", ip="1.2.3.4", redis=redis)
    assert exc_info.value.status_code == 429


async def test_fail_open_on_redis_error():
    """Redis connection failure → no exception raised (fail-open design)."""
    redis = AsyncMock()
    redis.eval.side_effect = ConnectionError("Redis down")
    # Must NOT raise — the fail-open design prevents Redis outages from locking users out
    await check_login_rate_limit("user@example.com", redis=redis)


# ── reset_login_rate_limit ───────────────────────────────────────────────────


async def test_reset_deletes_email_key():
    redis = _make_redis()
    await reset_login_rate_limit("user@example.com", redis=redis)
    redis.delete.assert_called_once_with("rate_limit:login:user@example.com")


async def test_reset_deletes_ip_key_when_provided():
    redis = _make_redis()
    await reset_login_rate_limit("user@example.com", ip="1.2.3.4", redis=redis)
    deleted_keys = [call.args[0] for call in redis.delete.call_args_list]
    assert "rate_limit:login:user@example.com" in deleted_keys
    assert "rate_limit:login:ip:1.2.3.4" in deleted_keys


async def test_reset_fails_silently():
    """A Redis failure during reset must not propagate — reset is non-critical."""
    redis = AsyncMock()
    redis.delete.side_effect = ConnectionError("Redis down")
    # Must NOT raise
    await reset_login_rate_limit("user@example.com", redis=redis)


# ── check_refresh_rate_limit ────────────────────────────────────────────────


def test_refresh_limit_is_60_per_minute():
    """Pin the constant. Reducing this (previously 10) logs legitimate users out after
    a handful of page reloads; raising it beyond 60 without reconsidering the threat
    model risks weakening DoS protection. Either direction should break this test."""
    assert REFRESH_RATE_LIMIT_IP_ATTEMPTS == 60


async def test_refresh_at_limit_does_not_raise():
    redis = _make_redis(count=REFRESH_RATE_LIMIT_IP_ATTEMPTS)
    await check_refresh_rate_limit(ip="1.2.3.4", redis=redis)


async def test_refresh_above_limit_raises_429():
    redis = _make_redis(count=REFRESH_RATE_LIMIT_IP_ATTEMPTS + 1, ttl=30)
    with pytest.raises(HTTPException) as exc_info:
        await check_refresh_rate_limit(ip="1.2.3.4", redis=redis)
    assert exc_info.value.status_code == 429
    assert exc_info.value.headers["Retry-After"] == "30"


async def test_refresh_missing_ip_uses_fallback_bucket():
    """No IP → shared 'unknown' bucket still enforced (not bypassed)."""
    redis = _make_redis(count=REFRESH_RATE_LIMIT_IP_ATTEMPTS + 1, ttl=10)
    with pytest.raises(HTTPException) as exc_info:
        await check_refresh_rate_limit(ip=None, redis=redis)
    assert exc_info.value.status_code == 429
    assert redis.eval.call_args.args[2] == "rate_limit:refresh:ip:unknown"


async def test_refresh_fail_open_on_redis_error():
    redis = AsyncMock()
    redis.eval.side_effect = ConnectionError("Redis down")
    await check_refresh_rate_limit(ip="1.2.3.4", redis=redis)
