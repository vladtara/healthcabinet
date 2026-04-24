import asyncio
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.exceptions import AccountSuspendedError, DuplicateEmailError, InvalidCredentialsError
from app.auth.models import User
from app.auth.repository import (
    create_consent_log,
    create_user,
    get_user_by_email,
    get_user_by_id_for_update,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

logger = structlog.get_logger()

# Lazily initialized dummy hash for constant-time comparison when no user is found.
# Without this, get_user_by_email returning None exits early and is measurably faster
# than a full bcrypt verify, enabling timing-based email enumeration attacks.
# Lazy to avoid: (a) bcrypt C extension crash at import time halting FastAPI startup,
# (b) breaking timing if bcrypt work factor is later increased (stale pre-computed hash
# would have lower cost, completing faster than live hashes and restoring the oracle).
_DUMMY_HASH: str | None = None


async def init_dummy_hash() -> None:
    """Pre-compute the dummy bcrypt hash at startup in a thread pool.

    Avoids blocking the asyncio event loop on the first login request.
    Called from the FastAPI lifespan startup handler.
    """
    global _DUMMY_HASH
    loop = asyncio.get_running_loop()
    _DUMMY_HASH = await loop.run_in_executor(None, hash_password, "__constant_time_dummy__")


async def _get_dummy_hash() -> str:
    # Fallback: if lifespan startup hasn't run (e.g. in tests that don't start the app),
    # compute in a thread pool to avoid blocking the event loop. This path should never
    # be hit in production since init_dummy_hash() runs before the server accepts requests.
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        loop = asyncio.get_running_loop()
        _DUMMY_HASH = await loop.run_in_executor(None, hash_password, "__constant_time_dummy__")
    return _DUMMY_HASH


async def login_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> tuple[User, str, str]:
    user = await get_user_by_email(db, email)
    # Always call verify_password — use dummy hash when user is None so timing is
    # identical regardless of whether the email exists (prevents enumeration).
    hashed = user.hashed_password if user is not None else await _get_dummy_hash()
    is_valid = verify_password(password, hashed)
    if not is_valid or user is None:
        raise InvalidCredentialsError()
    # Reject suspended accounts after credential verification (valid creds + suspended = 403)
    if user.account_status != "active":
        raise AccountSuspendedError()
    # Record last login timestamp on successful credential login only (not refresh)
    user.last_login_at = datetime.now(UTC)
    await db.flush()
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    return user, access_token, refresh_token


async def refresh_access_token(db: AsyncSession, refresh_token_str: str) -> tuple[str, str]:
    """Decode refresh JWT, verify the user still exists in the DB, issue new tokens.

    Returns (access_token, new_refresh_token). Token rotation means the old refresh
    cookie is superseded by the new one on every call, limiting the validity window of
    any stolen cookie to the time between two refresh operations.

    The DB lookup is critical for GDPR right-to-erasure: without it, deleted users can
    silently obtain new access tokens for the full 30-day refresh window post-deletion.
    """
    try:
        payload = decode_token(refresh_token_str)
    except ValueError as e:
        raise InvalidCredentialsError() from e
    if payload.get("type") != "refresh":
        raise InvalidCredentialsError()
    user_id_str: str = payload.get("sub", "")
    if not user_id_str:
        raise InvalidCredentialsError()
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError as e:
        raise InvalidCredentialsError() from e
    iat_raw = payload.get("iat")
    try:
        token_iat = datetime.fromtimestamp(int(iat_raw), tz=UTC) if iat_raw is not None else None
    except (TypeError, ValueError, OverflowError, OSError) as e:
        raise InvalidCredentialsError() from e
    # FOR UPDATE closes the concurrent revoke/refresh race — without it, a refresh
    # started before a revoke commits can snapshot tokens_invalid_before=NULL and
    # mint a token whose iat lands strictly after the revocation cutoff, producing
    # a genuinely post-revoke token that bypasses the check forever.
    user = await get_user_by_id_for_update(db, user_id)
    if user is None:
        raise InvalidCredentialsError()
    # Reject refresh tokens issued before an admin revocation. Treated as InvalidCredentials
    # (not AccountSuspended) so the clear-cookie path runs and the user is redirected to /login
    # — the account is still active, they simply need to re-authenticate.
    if user.tokens_invalid_before is not None and (
        token_iat is None or token_iat < user.tokens_invalid_before
    ):
        raise InvalidCredentialsError()
    # Reject suspended accounts on refresh — forces logout per AC #3
    if user.account_status != "active":
        raise AccountSuspendedError()
    access_token = create_access_token(subject=str(user.id))
    new_refresh_token = create_refresh_token(subject=str(user.id))
    return access_token, new_refresh_token


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    privacy_policy_version: str,
) -> tuple[User, str, str]:
    existing = await get_user_by_email(db, email)
    if existing:
        raise DuplicateEmailError()

    hashed = hash_password(password)
    try:
        async with db.begin_nested():
            user = await create_user(db, email, hashed)
            await create_consent_log(
                db,
                user_id=user.id,
                consent_type="health_data_processing",
                privacy_policy_version=privacy_policy_version,
            )
    except IntegrityError:
        raise DuplicateEmailError() from None
    # Commit explicitly before issuing tokens so the user row is visible to subsequent
    # requests. Without this, FastAPI sends the HTTP response before get_db teardown
    # runs await session.commit(), meaning a client reusing the token immediately can
    # get 401 from get_current_user → get_user_by_id on a fresh DB session that hasn't
    # seen the uncommitted row yet. get_db's post-yield commit becomes a no-op on the
    # already-committed session.
    await db.commit()
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    return user, access_token, refresh_token


async def ensure_bootstrap_admin(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    privacy_policy_version: str,
) -> User:
    """Ensure the configured bootstrap admin exists and can authenticate."""

    user = await get_user_by_email(db, email)
    if user is None:
        hashed = hash_password(password)
        async with db.begin_nested():
            user = await create_user(db, email, hashed, role="admin")
            await create_consent_log(
                db,
                user_id=user.id,
                consent_type="health_data_processing",
                privacy_policy_version=privacy_policy_version,
            )
        await db.commit()
        logger.info("auth.bootstrap_admin.created", email=user.email)
        return user

    updated_fields: list[str] = []
    if user.role != "admin":
        user.role = "admin"
        updated_fields.append("role")
    if user.account_status != "active":
        user.account_status = "active"
        updated_fields.append("account_status")

    if updated_fields:
        await db.commit()
        await db.refresh(user)
        logger.info(
            "auth.bootstrap_admin.updated",
            email=user.email,
            updated_fields=updated_fields,
        )
    else:
        logger.info("auth.bootstrap_admin.exists", email=user.email)

    return user
