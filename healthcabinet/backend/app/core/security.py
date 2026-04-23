import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
import structlog
from jwt import InvalidTokenError

from app.core.config import settings

logger = structlog.get_logger()

ALGORITHM = "HS256"

# python-jose was replaced with PyJWT (actively maintained, audited) because python-jose
# has been largely unmaintained since mid-2023 and has open CVEs — unacceptable for a
# health-data application. PyJWT provides the same encode/decode API; the only change is
# the error base class (InvalidTokenError instead of JWTError).

# Direct bcrypt usage is intentional: passlib[bcrypt] 1.7.4 is incompatible with
# bcrypt >= 4.0 (passlib's detect_wrap_bug() crashes with the new ValueError semantics).
# The passlib[bcrypt] dependency remains in pyproject.toml for future migration once
# passlib releases a compatible version. This implementation is functionally equivalent
# to passlib's verify/hash API — no silent truncation: passwords > 72 bytes are rejected
# by LoginRequest/RegisterRequest validators before reaching these functions.


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        # Corrupt or malformed hash in DB (e.g. wrong prefix, truncated value) — log and
        # return False so the caller raises a 401 rather than leaking a 500 to the client.
        logger.error("security.verify_password_failed", reason="corrupt_hash")
        return False
    # All other exceptions (MemoryError, bcrypt C-extension errors, etc.) propagate as 500
    # so operators receive an alert rather than a silent phantom "wrong password" failure.


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    # iat is required for admin-initiated session revocation — validators compare it against
    # User.tokens_invalid_before and reject any token issued before a revocation event.
    payload: dict[str, Any] = {"sub": subject, "exp": expire, "iat": now, "type": "access"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str) -> str:
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload: dict[str, Any] = {"sub": subject, "exp": expire, "iat": now, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_access_token(token: str) -> uuid.UUID:
    """Validate a raw access token string and return the user_id UUID.

    Used by the SSE endpoint for both Authorization header and legacy query-param
    auth paths. Can be removed when query-param support is dropped.
    Raises HTTP 401 if the token is missing, expired, or not an access token.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("Expected access token")
        user_id_str: str = payload.get("sub", "")
        if not user_id_str:
            raise ValueError("Missing subject in token")
        return uuid.UUID(user_id_str)
    except ValueError as e:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}") from e
