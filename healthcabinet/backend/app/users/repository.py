import json
import uuid
from dataclasses import dataclass
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_bytes, encrypt_bytes
from app.users.models import UserProfile

logger = structlog.get_logger()


@dataclass(slots=True)
class ProfileContext:
    """Decrypted subset of UserProfile used to build the AI prompt profile block.

    Only fields the assistant should see are populated. Height/weight are not
    PHI in isolation and not clinically relevant for the lab-interpretation
    assistant; omitted here deliberately.
    """

    age: int | None
    sex: str | None
    known_conditions: list[str]
    medications: list[str]
    family_history: str | None

    def is_empty(self) -> bool:
        return (
            self.age is None
            and not self.sex
            and not self.known_conditions
            and not self.medications
            and not self.family_history
        )


async def get_user_profile(db: AsyncSession, user_id: uuid.UUID) -> UserProfile | None:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    return result.scalar_one_or_none()


def _encrypted_fields_for(fields: dict[str, Any]) -> dict[str, bytes | None]:
    """Given the plaintext field kwargs for an upsert, produce the matching
    ciphertext kwargs. Only fields that are actually being written (present in
    `fields`) get an encrypted counterpart — avoids clobbering existing
    ciphertext on partial updates.
    """
    out: dict[str, bytes | None] = {}
    if "age" in fields:
        out["age_encrypted"] = (
            encrypt_bytes(str(fields["age"]).encode("utf-8")) if fields["age"] is not None else None
        )
    if "sex" in fields:
        out["sex_encrypted"] = (
            encrypt_bytes(fields["sex"].encode("utf-8")) if fields["sex"] else None
        )
    if "known_conditions" in fields:
        kc = fields["known_conditions"]
        out["known_conditions_encrypted"] = (
            encrypt_bytes(json.dumps(kc).encode("utf-8")) if kc is not None else None
        )
    if "medications" in fields:
        meds = fields["medications"]
        out["medications_encrypted"] = (
            encrypt_bytes(json.dumps(meds).encode("utf-8")) if meds is not None else None
        )
    if "family_history" in fields:
        fh = fields["family_history"]
        out["family_history_encrypted"] = (
            encrypt_bytes(fh.encode("utf-8")) if fh else None
        )
    return out


async def upsert_user_profile(db: AsyncSession, user_id: uuid.UUID, **fields: Any) -> UserProfile:
    # Dual-write: plaintext columns keep the wire contract with ProfileResponse
    # (which reads them via from_attributes=True); encrypted columns satisfy
    # the phase-1 encryption migration. Phase-2 drops plaintext columns.
    encrypted_fields = _encrypted_fields_for(fields)
    insert_values: dict[str, Any] = {"user_id": user_id, **fields, **encrypted_fields}

    update_set: dict[str, Any] = {**fields, **encrypted_fields}
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


def _decrypt_text(blob: bytes | None) -> str | None:
    if blob is None:
        return None
    try:
        return decrypt_bytes(blob).decode("utf-8")
    except Exception:
        logger.warning("user_profile.decrypt_failed")
        return None


def _decrypt_json_list(blob: bytes | None) -> list[str]:
    if blob is None:
        return []
    try:
        raw = json.loads(decrypt_bytes(blob).decode("utf-8"))
    except Exception:
        logger.warning("user_profile.decrypt_json_failed")
        return []
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if isinstance(item, (str, int, float))]


async def get_profile_context(
    db: AsyncSession, user_id: uuid.UUID
) -> ProfileContext | None:
    """Decrypt the fields the AI assistant needs and return a typed bundle.

    Prefers ciphertext columns (populated by phase-1 migration + dual-write on
    every subsequent upsert). Falls back to plaintext when the encrypted column
    is NULL — happens only for rows that existed before the phase-1 migration
    and have not been re-saved since (the migration backfills in-place, but a
    no-key migration run can skip the backfill).
    """
    row = await get_user_profile(db, user_id)
    if row is None:
        return None

    def _age_from_ciphertext(blob: bytes | None) -> int | None:
        text = _decrypt_text(blob)
        if text is None:
            return None
        try:
            return int(text)
        except ValueError:
            return None

    age = _age_from_ciphertext(row.age_encrypted)
    if age is None:
        age = row.age
    sex = _decrypt_text(row.sex_encrypted)
    if sex is None:
        sex = row.sex

    known_conditions = _decrypt_json_list(row.known_conditions_encrypted)
    # Empty list is a legitimate value; fall back to plaintext only when there
    # is no ciphertext at all (migration-gap case).
    if (
        not known_conditions
        and row.known_conditions_encrypted is None
        and row.known_conditions
    ):
        known_conditions = list(row.known_conditions)
    medications = _decrypt_json_list(row.medications_encrypted)
    if not medications and row.medications_encrypted is None and row.medications:
        medications = list(row.medications)

    family_history = _decrypt_text(row.family_history_encrypted)
    if family_history is None:
        family_history = row.family_history

    return ProfileContext(
        age=age,
        sex=sex,
        known_conditions=known_conditions,
        medications=medications,
        family_history=family_history,
    )


__all__ = [
    "ProfileContext",
    "get_user_profile",
    "get_profile_context",
    "update_onboarding_step",
    "upsert_user_profile",
]
