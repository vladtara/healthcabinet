"""
Auth dependency injection.

CRITICAL: user_id ALWAYS comes from Depends(get_current_user) — NEVER from request body or
query params. This pattern is established here and enforced across all domains.
"""

import uuid
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.repository import get_user_by_id
from app.core.database import get_db
from app.core.security import decode_token

security = HTTPBearer()


async def resolve_access_token(token: str, db: AsyncSession) -> User:
    """Validate a raw access token and return the authenticated User.

    Shared by the Authorization-header dependency (`get_current_user`) and the SSE
    stream endpoint — the latter accepts the token via query-string for EventSource
    clients that cannot send headers, and must apply the same revocation + suspension
    checks to avoid bypass.

    Raises HTTPException 401 on any invalid or revoked token, 403 on suspended account.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("Expected access token")
        user_id_str: str = payload.get("sub", "")
        if not user_id_str:
            raise ValueError("Missing subject in token")
        user_id = uuid.UUID(user_id_str)
        iat_raw = payload.get("iat")
        # OverflowError/OSError: forged iat like 1e20 blows past POSIX timestamp range.
        # TypeError: iat shaped as list/dict/None-after-get survives decode_token but
        # breaks int(). Without these, a crafted token yields 500 instead of 401.
        token_iat = datetime.fromtimestamp(int(iat_raw), tz=UTC) if iat_raw is not None else None
    except (TypeError, ValueError, OverflowError, OSError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Reject tokens issued before the user's last session-revocation event.
    # Tokens minted after a revoke still carry an iat >= tokens_invalid_before and pass.
    # Missing iat (legacy tokens predating this field) is treated as revoked when a
    # revocation timestamp exists — any legacy token must be re-issued post-revoke.
    if user.tokens_invalid_before is not None and (
        token_iat is None or token_iat < user.tokens_invalid_before
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Reject suspended accounts — existing access tokens stop working immediately
    if user.account_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended",
        )
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate JWT from Authorization header. Returns current user from DB."""
    return await resolve_access_token(credentials.credentials, db)


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role. Raises 403 if user is not admin."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


async def require_paid_tier(current_user: User = Depends(get_current_user)) -> User:
    """Require paid subscription tier. Raises 403 if user is on free tier."""
    if current_user.tier != "paid":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Paid subscription required"
        )
    return current_user
