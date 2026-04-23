import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import UserProfile


async def get_user_profile(db: AsyncSession, user_id: uuid.UUID) -> UserProfile | None:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    return result.scalar_one_or_none()


async def upsert_user_profile(db: AsyncSession, user_id: uuid.UUID, **fields: Any) -> UserProfile:
    insert_values: dict[str, Any] = {"user_id": user_id, **fields}

    # Build the set clause for the ON CONFLICT DO UPDATE branch — excludes user_id
    update_set: dict[str, Any] = dict(fields.items())
    update_set["updated_at"] = func.now()

    stmt = (
        insert(UserProfile)
        .values(**insert_values)
        .on_conflict_do_update(
            index_elements=["user_id"],
            set_=update_set,
        )
        .returning(UserProfile.id)
    )

    result = await db.execute(stmt)
    row_id = result.scalar_one()
    await db.flush()

    profile_result = await db.execute(select(UserProfile).where(UserProfile.id == row_id))
    profile = profile_result.scalar_one()
    await db.refresh(profile)
    return profile


async def update_onboarding_step(db: AsyncSession, user_id: uuid.UUID, step: int) -> UserProfile:
    return await upsert_user_profile(db, user_id, onboarding_step=step)
