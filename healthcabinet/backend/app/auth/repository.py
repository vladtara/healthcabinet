import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.users.models import ConsentLog


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_id_for_update(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Row-locking variant used by the refresh flow.

    Without FOR UPDATE, a refresh in flight during an admin session-revocation can
    read the pre-revoke snapshot (tokens_invalid_before=NULL), mint a fresh access
    token with iat > cutoff, and hand it to the caller — the token then passes every
    subsequent validation because its iat is genuinely after the stored cutoff. The
    lock forces refresh to wait until the revocation commits, closing the race at
    the cost of briefly serializing concurrent refreshes for a single user.
    """
    result = await db.execute(
        select(User).where(User.id == user_id).with_for_update()
    )
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    hashed_password: str,
    *,
    role: str = "user",
    tier: str = "free",
) -> User:
    # Normalize to lowercase so stored email always matches get_user_by_email's lookup.
    # Guards against callers that bypass Pydantic's EmailStr normalization (DB seeds, admin tools).
    user = User(email=email.lower(), hashed_password=hashed_password, role=role, tier=tier)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    # Normalize to lowercase for case-insensitive lookup — guards against callers
    # that bypass Pydantic's EmailStr normalization (e.g. direct DB seeds or admin tools).
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def list_consent_logs_by_user(
    db: AsyncSession, user_id: uuid.UUID
) -> list[ConsentLog]:
    """Return all consent log entries for a user, ordered by consented_at."""
    result = await db.execute(
        select(ConsentLog)
        .where(ConsentLog.user_id == user_id)
        .order_by(ConsentLog.consented_at)
    )
    return list(result.scalars().all())


async def list_consent_logs_by_user_desc(
    db: AsyncSession, user_id: uuid.UUID
) -> list[ConsentLog]:
    """Return all consent log entries for a user, ordered by consented_at descending."""
    result = await db.execute(
        select(ConsentLog)
        .where(ConsentLog.user_id == user_id)
        .order_by(ConsentLog.consented_at.desc())
    )
    return list(result.scalars().all())


async def create_consent_log(
    db: AsyncSession,
    user_id: uuid.UUID,
    consent_type: str,
    privacy_policy_version: str,
) -> ConsentLog:
    consent_log = ConsentLog(
        user_id=user_id,
        consent_type=consent_type,
        privacy_policy_version=privacy_policy_version,
    )
    db.add(consent_log)
    await db.flush()
    await db.refresh(consent_log)
    return consent_log
