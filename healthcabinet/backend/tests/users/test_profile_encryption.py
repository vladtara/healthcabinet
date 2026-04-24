"""Tests for AES-GCM encryption of UserProfile PHI fields (phase-1 migration).

These tests exercise the dual-write behavior introduced with phase-1:
encrypted columns are populated alongside plaintext columns on every upsert,
and `get_profile_context` returns decrypted values from ciphertext when
present.
"""

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_bytes
from app.users import repository as users_repository
from app.users.repository import ProfileContext, get_profile_context, upsert_user_profile


@pytest.mark.asyncio
async def test_upsert_writes_encrypted_columns(
    async_db_session: AsyncSession,
    make_user,
):
    user, _ = await make_user(email="encpx@example.com")

    profile = await upsert_user_profile(
        async_db_session,
        user.id,
        age=42,
        sex="female",
        known_conditions=["hypothyroidism", "migraine"],
        medications=["levothyroxine 75 mcg"],
        family_history="type 2 diabetes (father)",
    )

    # Ciphertext columns populated; plaintext columns also populated during
    # phase-1 dual-write so ProfileResponse keeps working.
    assert profile.age == 42
    assert profile.age_encrypted is not None
    assert profile.age_encrypted != b"42"
    # GCM ciphertext is at minimum 28 bytes (12 nonce + 16 tag).
    assert len(profile.age_encrypted) >= 28
    assert decrypt_bytes(profile.age_encrypted).decode() == "42"

    assert profile.sex_encrypted is not None
    assert decrypt_bytes(profile.sex_encrypted).decode() == "female"

    assert profile.known_conditions_encrypted is not None
    assert json.loads(decrypt_bytes(profile.known_conditions_encrypted)) == [
        "hypothyroidism",
        "migraine",
    ]

    assert profile.medications_encrypted is not None
    assert json.loads(decrypt_bytes(profile.medications_encrypted)) == [
        "levothyroxine 75 mcg"
    ]

    assert profile.family_history_encrypted is not None
    assert (
        decrypt_bytes(profile.family_history_encrypted).decode()
        == "type 2 diabetes (father)"
    )


@pytest.mark.asyncio
async def test_get_profile_context_roundtrip(
    async_db_session: AsyncSession,
    make_user,
):
    user, _ = await make_user(email="ctxroundtrip@example.com")
    await upsert_user_profile(
        async_db_session,
        user.id,
        age=34,
        sex="male",
        known_conditions=["asthma"],
        medications=["albuterol inhaler"],
        family_history="hypertension (mother)",
    )
    await async_db_session.flush()

    ctx = await get_profile_context(async_db_session, user.id)
    assert ctx is not None
    assert ctx.age == 34
    assert ctx.sex == "male"
    assert ctx.known_conditions == ["asthma"]
    assert ctx.medications == ["albuterol inhaler"]
    assert ctx.family_history == "hypertension (mother)"
    assert ctx.is_empty() is False


@pytest.mark.asyncio
async def test_get_profile_context_empty_user(
    async_db_session: AsyncSession,
    make_user,
):
    user, _ = await make_user(email="emptyctx@example.com")
    # No profile row at all.
    assert await get_profile_context(async_db_session, user.id) is None

    # Profile row with all fields empty → ProfileContext.is_empty() is True.
    await upsert_user_profile(async_db_session, user.id, onboarding_step=1)
    ctx = await get_profile_context(async_db_session, user.id)
    assert ctx is not None
    assert ctx.is_empty() is True


@pytest.mark.asyncio
async def test_partial_update_preserves_other_ciphertext(
    async_db_session: AsyncSession,
    make_user,
):
    user, _ = await make_user(email="partial@example.com")
    await upsert_user_profile(
        async_db_session,
        user.id,
        age=50,
        sex="other",
        known_conditions=["hypertension"],
    )

    # Update only sex; conditions ciphertext should stay intact.
    await upsert_user_profile(
        async_db_session,
        user.id,
        sex="female",
    )

    ctx = await get_profile_context(async_db_session, user.id)
    assert ctx is not None
    assert ctx.sex == "female"
    assert ctx.age == 50
    assert ctx.known_conditions == ["hypertension"]


@pytest.mark.asyncio
async def test_cascade_delete_removes_profile(
    async_db_session: AsyncSession,
    make_user,
):
    """Deleting a user cascades to user_profiles via the existing FK."""
    from sqlalchemy import delete, select

    from app.auth.models import User
    from app.users.models import UserProfile

    user, _ = await make_user(email="cascade@example.com")
    await upsert_user_profile(async_db_session, user.id, age=30, sex="female")
    await async_db_session.flush()

    await async_db_session.execute(delete(User).where(User.id == user.id))
    await async_db_session.flush()

    result = await async_db_session.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_profile_context_ignores_height_and_weight(
    async_db_session: AsyncSession,
    make_user,
):
    """ProfileContext is the AI-facing bundle; height/weight are intentionally
    excluded. They're plaintext and not clinically used for lab interpretation."""
    user, _ = await make_user(email="noheight@example.com")
    await upsert_user_profile(
        async_db_session,
        user.id,
        age=28,
        sex="female",
        height_cm=170,
        weight_kg=65,
    )

    ctx = await get_profile_context(async_db_session, user.id)
    assert ctx is not None
    assert ctx.age == 28
    # ProfileContext dataclass has no height/weight — verify attribute absence.
    assert not hasattr(ctx, "height_cm")
    assert not hasattr(ctx, "weight_kg")


@pytest.mark.asyncio
async def test_get_profile_context_falls_back_to_plaintext_for_pre_migration_rows(
    async_db_session: AsyncSession,
    make_user,
):
    """Rows that existed before phase-1 and never got re-saved keep their
    plaintext values and have NULL encrypted columns. The fallback path must
    still return the data for AI context until phase-2 drops plaintext."""
    from sqlalchemy import update

    from app.users.models import UserProfile

    user, _ = await make_user(email="legacy@example.com")
    # Write with the current dual-write path, then null out ciphertext to
    # simulate the legacy state.
    await upsert_user_profile(
        async_db_session,
        user.id,
        age=40,
        sex="female",
        known_conditions=["migraine"],
        medications=["ibuprofen"],
        family_history="none",
    )
    await async_db_session.execute(
        update(UserProfile)
        .where(UserProfile.user_id == user.id)
        .values(
            age_encrypted=None,
            sex_encrypted=None,
            known_conditions_encrypted=None,
            medications_encrypted=None,
            family_history_encrypted=None,
        )
    )
    await async_db_session.flush()

    ctx = await get_profile_context(async_db_session, user.id)
    assert ctx is not None
    assert ctx.age == 40
    assert ctx.sex == "female"
    assert ctx.known_conditions == ["migraine"]
    assert ctx.medications == ["ibuprofen"]
    assert ctx.family_history == "none"


@pytest.mark.asyncio
async def test_profile_context_module_export(async_db_session: AsyncSession) -> None:
    """ProfileContext is surfaced at module level for service.py to import."""
    assert hasattr(users_repository, "ProfileContext")
    assert ProfileContext is users_repository.ProfileContext
