"""
Documents dependency injection — domain-specific dependencies only.

rate_limit_upload: per-user daily upload quota (free tier: 5/day, paid: unlimited).
get_arq_redis: returns the ARQ Redis pool from app.state (injected in lifespan).
"""

import inspect
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import Depends, Request

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.rate_limit import _LUA_INCR_EXPIRE, get_redis
from app.documents.exceptions import UploadLimitExceededError

logger = structlog.get_logger()

UPLOAD_RATE_LIMIT_FREE = 5  # free tier: 5 uploads per day
UPLOAD_RATE_LIMIT_WINDOW = 86400  # 24-hour window in seconds


async def rate_limit_upload(
    current_user: User = Depends(get_current_user),
) -> None:
    """Enforce daily upload quota.

    Paid users are unlimited. Free users are capped at 5 uploads/day.
    Uses the same atomic Lua INCR+EXPIRE pattern as login rate limiting.
    Fails open on Redis unavailability — a Redis outage must not block uploads.
    """
    if current_user.tier == "paid":
        return  # unlimited for paid tier

    key = f"uploads:{current_user.id}:{datetime.now(UTC).date().isoformat()}"
    try:
        redis = await get_redis()
        maybe_count = redis.eval(_LUA_INCR_EXPIRE, 1, key, str(UPLOAD_RATE_LIMIT_WINDOW))
        raw_count = await maybe_count if inspect.isawaitable(maybe_count) else maybe_count
        count = int(raw_count)
        if count > UPLOAD_RATE_LIMIT_FREE:
            raise UploadLimitExceededError()
    except UploadLimitExceededError:
        raise
    except Exception:
        logger.warning("rate_limit.redis_unavailable", endpoint="upload")


async def get_arq_redis(request: Request) -> Any:
    """Return the ARQ Redis pool from application state (set up in lifespan)."""
    return request.app.state.arq_redis
