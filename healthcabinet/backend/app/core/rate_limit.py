"""
Login rate limiting using atomic Lua eval (INCR + EXPIRE in a single Redis round-trip).

Two-layer protection:
- Per-email: 10 attempts per 60s — stops single-account brute force.
- Per-IP: 50 attempts per 60s — stops credential stuffing (one IP, many emails).

Refresh rate limiting:
- Per-IP: 60 calls per 60s — sized for reload churn + NAT'd IPs, NOT as the
  primary stolen-cookie defence. The real protections are httpOnly + Secure +
  SameSite=Strict cookie attributes and admin session revocation
  (users.tokens_invalid_before). This bucket is a coarse abuse ceiling; at
  60/min an attacker with a stolen cookie still mints up to 86 400 tokens/day,
  so do not tighten this knob as a way to block theft — revoke the session.
  A lower cap (previously 10) caused legitimate users to be logged out after
  a handful of page reloads, with no meaningful security improvement.

Counter is reset on successful login (per-email only) so legitimate users are never
locked out from normal activity. Fails open on Redis unavailability so an outage never
locks users out of their accounts.
"""

from collections.abc import Callable
from typing import cast

import redis.asyncio as aioredis
import structlog
from fastapi import HTTPException, status

from app.core.config import settings

logger = structlog.get_logger()

LOGIN_RATE_LIMIT_ATTEMPTS = 10  # max per-email login attempts per window
LOGIN_RATE_LIMIT_IP_ATTEMPTS = 50  # max per-IP login attempts per window
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 60  # 1-minute window for login keys
REFRESH_RATE_LIMIT_IP_ATTEMPTS = 60  # max per-IP refresh attempts per window
REFRESH_RATE_LIMIT_WINDOW_SECONDS = 60  # 1-minute window for refresh key
REGISTER_RATE_LIMIT_IP_ATTEMPTS = 10  # max per-IP registration attempts per window
REGISTER_RATE_LIMIT_WINDOW_SECONDS = 300  # 5-minute window for registration key

# Lua script: atomically INCR a key and set its TTL only on the first increment.
# Without atomicity, a Redis connection drop between INCR and EXPIRE leaves the key
# with no TTL → the counter accumulates indefinitely → permanent user lockout.
_LUA_INCR_EXPIRE = """
local count = redis.call("INCR", KEYS[1])
if count == 1 then
  redis.call("EXPIRE", KEYS[1], ARGV[1])
end
return count
"""

_REDIS_FROM_URL = cast(Callable[..., aioredis.Redis], aioredis.from_url)
_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Return the shared Redis client, creating it lazily on first call.

    Exposed as a public function so it can be overridden via
    app.dependency_overrides in tests.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = _REDIS_FROM_URL(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def _check_key(
    redis: aioredis.Redis,
    key: str,
    limit: int,
    window_seconds: int = LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    error_message: str = "Too many login attempts",
) -> None:
    """Increment key and raise HTTP 429 if limit exceeded.

    Uses a Lua script to atomically INCR and EXPIRE on first increment, preventing
    a race condition where a dropped connection between INCR and EXPIRE would leave
    the key with no TTL and cause a permanent lockout.
    """
    count = await redis.eval(_LUA_INCR_EXPIRE, 1, key, str(window_seconds))  # type: ignore[misc]
    if count > limit:
        ttl = await redis.ttl(key)
        if ttl == -2:
            # Key expired between INCR and TTL call — window has reset, client can retry now.
            retry_after = 1
        elif ttl == -1:
            # Key has no TTL — Lua script bug or Redis persistence anomaly; log and use window.
            logger.error("rate_limit.key_missing_ttl", key=key)
            retry_after = window_seconds
        else:
            retry_after = max(ttl, 1)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"{error_message}. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


async def check_login_rate_limit(
    email: str,
    ip: str | None = None,
    redis: aioredis.Redis | None = None,
) -> None:
    """Check login rate limit for the given email and (optional) IP.

    Raises HTTP 429 if either the per-email (10/min) or per-IP (50/min)
    limit is exceeded.  Fails open on Redis unavailability so a Redis
    outage never locks users out.

    Args:
        email: Caller's email address (per-account key).
        ip:    Caller's IP address (per-IP secondary key). Omit to skip IP check.
        redis: Injected Redis client (for unit tests). Fetched lazily if None.
    """
    try:
        r = redis if redis is not None else await get_redis()
        await _check_key(r, f"rate_limit:login:{email.lower()}", LOGIN_RATE_LIMIT_ATTEMPTS)
        if ip:
            await _check_key(r, f"rate_limit:login:ip:{ip}", LOGIN_RATE_LIMIT_IP_ATTEMPTS)
    except HTTPException:
        raise
    except Exception:
        # Fail open — rate limiting is best-effort; Redis outage ≠ lockout
        logger.warning("rate_limit.redis_unavailable", email_prefix=email[:3] + "***")


async def check_refresh_rate_limit(
    ip: str | None = None,
    redis: aioredis.Redis | None = None,
) -> None:
    """Check refresh token rate limit — per-IP only (60/min).

    Coarse abuse ceiling, not the primary stolen-cookie defence. Stolen refresh cookies
    are addressed by cookie attributes (httpOnly + Secure + SameSite=Strict) and by
    admin session revocation; this limit exists so a single IP cannot hammer the
    endpoint into a denial of service. Per-email is not applicable here since the
    refresh endpoint does not accept an email parameter. Fails open on Redis
    unavailability.

    Args:
        ip:    Caller's IP address. Omit to skip (e.g. when IP is unavailable).
        redis: Injected Redis client (for unit tests). Fetched lazily if None.
    """
    if not ip:
        # Fall back to a shared "unknown-ip" bucket rather than skipping rate limiting
        # entirely. This prevents unlimited token generation when the proxy strips the IP.
        logger.warning(
            "rate_limit.ip_unavailable", endpoint="refresh", fallback="unknown-ip bucket"
        )
        ip = "unknown"
    try:
        r = redis if redis is not None else await get_redis()
        await _check_key(
            r,
            f"rate_limit:refresh:ip:{ip}",
            REFRESH_RATE_LIMIT_IP_ATTEMPTS,
            window_seconds=REFRESH_RATE_LIMIT_WINDOW_SECONDS,
            error_message="Too many refresh attempts",
        )
    except HTTPException:
        raise
    except Exception:
        logger.warning("rate_limit.redis_unavailable", endpoint="refresh")


async def check_register_rate_limit(
    ip: str | None = None,
    redis: aioredis.Redis | None = None,
) -> None:
    """Check registration rate limit — per-IP only (10 attempts per 5 minutes).

    Prevents bulk email enumeration (409 = exists, 201 = doesn't) and CPU exhaustion
    via unbounded bcrypt calls. Falls back to a shared bucket when IP is unavailable.
    Fails open on Redis unavailability.

    Args:
        ip:    Caller's IP address. Falls back to "unknown" bucket if None.
        redis: Injected Redis client (for unit tests). Fetched lazily if None.
    """
    effective_ip = ip if ip else "unknown"
    if not ip:
        logger.warning(
            "rate_limit.ip_unavailable", endpoint="register", fallback="unknown-ip bucket"
        )
    try:
        r = redis if redis is not None else await get_redis()
        await _check_key(
            r,
            f"rate_limit:register:ip:{effective_ip}",
            REGISTER_RATE_LIMIT_IP_ATTEMPTS,
            window_seconds=REGISTER_RATE_LIMIT_WINDOW_SECONDS,
            error_message="Too many registration attempts",
        )
    except HTTPException:
        raise
    except Exception:
        logger.warning("rate_limit.redis_unavailable", endpoint="register")


AI_PATTERNS_RATE_LIMIT_ATTEMPTS = 10  # max per-user calls per window
AI_PATTERNS_RATE_LIMIT_WINDOW_SECONDS = 60  # 1-minute window


async def check_ai_patterns_rate_limit(
    user_id: str,
    redis: aioredis.Redis | None = None,
) -> None:
    """Check AI pattern detection rate limit — per-user (10 calls/min).

    Prevents unbounded Claude API spending from a single authenticated user.
    Fails open on Redis unavailability so a Redis outage never blocks users.

    Args:
        user_id: Authenticated user's UUID as a string.
        redis:   Injected Redis client (for unit tests). Fetched lazily if None.
    """
    try:
        r = redis if redis is not None else await get_redis()
        await _check_key(
            r,
            f"rate_limit:ai_patterns:user:{user_id}",
            AI_PATTERNS_RATE_LIMIT_ATTEMPTS,
            window_seconds=AI_PATTERNS_RATE_LIMIT_WINDOW_SECONDS,
            error_message="Too many pattern detection requests",
        )
    except HTTPException:
        raise
    except Exception:
        logger.warning("rate_limit.redis_unavailable", endpoint="ai_patterns")


# Story 15.3 — dashboard-scoped aggregate AI endpoints.
# Tighter window than patterns because each call can aggregate N documents.
AI_DASHBOARD_RATE_LIMIT_ATTEMPTS = 10
AI_DASHBOARD_RATE_LIMIT_WINDOW_SECONDS = 60


async def check_ai_dashboard_rate_limit(
    user_id: str,
    redis: aioredis.Redis | None = None,
) -> None:
    """Check dashboard-scoped AI endpoint rate limit — per-user (10 calls/min).

    Applies to GET /ai/dashboard/interpretation and POST /ai/dashboard/chat.
    Each call aggregates context over every contributing AiMemory row, so
    unbounded calls are particularly expensive. Fails open on Redis outage.
    """
    try:
        r = redis if redis is not None else await get_redis()
        await _check_key(
            r,
            f"rate_limit:ai_dashboard:user:{user_id}",
            AI_DASHBOARD_RATE_LIMIT_ATTEMPTS,
            window_seconds=AI_DASHBOARD_RATE_LIMIT_WINDOW_SECONDS,
            error_message="Too many dashboard AI requests",
        )
    except HTTPException:
        raise
    except Exception:
        logger.warning("rate_limit.redis_unavailable", endpoint="ai_dashboard")


async def reset_login_rate_limit(
    email: str,
    ip: str | None = None,
    redis: aioredis.Redis | None = None,
) -> None:
    """Reset rate limit counters after a successful login.

    Prevents legitimate users from being locked out after 10 successful logins
    in a 60-second window (e.g. automated scripts or QA environments). Fails
    silently — a reset failure is non-critical.

    Args:
        email: Logged-in user's email address.
        ip:    Caller's IP address (optional; resets IP counter too when given).
        redis: Injected Redis client (for unit tests). Fetched lazily if None.
    """
    try:
        r = redis if redis is not None else await get_redis()
        await r.delete(f"rate_limit:login:{email.lower()}")
        if ip:
            await r.delete(f"rate_limit:login:ip:{ip}")
    except Exception:
        logger.warning("rate_limit.reset_failed", email_prefix=email[:3] + "***")
