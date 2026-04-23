from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.service import ensure_bootstrap_admin
from app.core.security import verify_password
from app.users.models import ConsentLog


async def test_ensure_bootstrap_admin_creates_new_admin_user(async_db_session: AsyncSession):
    user = await ensure_bootstrap_admin(
        async_db_session,
        email="bootstrap-admin@example.com",
        password="bootstrap-pass-123",
        privacy_policy_version="1.0",
    )

    assert user.email == "bootstrap-admin@example.com"
    assert user.role == "admin"
    assert user.account_status == "active"
    assert verify_password("bootstrap-pass-123", user.hashed_password)

    consent_result = await async_db_session.execute(
        select(ConsentLog).where(ConsentLog.user_id == user.id)
    )
    consent_log = consent_result.scalar_one_or_none()
    assert consent_log is not None
    assert consent_log.privacy_policy_version == "1.0"


async def test_ensure_bootstrap_admin_promotes_and_reactivates_existing_user(
    async_db_session: AsyncSession,
    make_user,
):
    user, original_password = await make_user(email="existing-admin@example.com")
    user.account_status = "suspended"
    await async_db_session.flush()

    bootstrapped = await ensure_bootstrap_admin(
        async_db_session,
        email="existing-admin@example.com",
        password="ignored-new-password-123",
        privacy_policy_version="1.0",
    )

    assert bootstrapped.id == user.id
    assert bootstrapped.role == "admin"
    assert bootstrapped.account_status == "active"
    assert verify_password(original_password, bootstrapped.hashed_password)
    assert not verify_password("ignored-new-password-123", bootstrapped.hashed_password)


async def test_ensure_bootstrap_admin_is_idempotent(async_db_session: AsyncSession):
    first = await ensure_bootstrap_admin(
        async_db_session,
        email="idempotent-admin@example.com",
        password="bootstrap-pass-123",
        privacy_policy_version="1.0",
    )
    second = await ensure_bootstrap_admin(
        async_db_session,
        email="idempotent-admin@example.com",
        password="another-password-123",
        privacy_policy_version="1.0",
    )

    users_result = await async_db_session.execute(
        select(User).where(User.email == "idempotent-admin@example.com")
    )
    users = users_result.scalars().all()

    assert first.id == second.id
    assert len(users) == 1
