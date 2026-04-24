"""user_profile_encryption_phase1

Phase-1 of two-phase migration that moves PHI columns on `user_profiles`
to AES-256-GCM encrypted-at-rest storage.

Phase-1 (this migration):
- Add `*_encrypted` BYTEA columns beside the existing plaintext columns.
- Backfill existing rows by encrypting the current plaintext values.
- Add CHECK constraints on ciphertext length (>= 28 bytes = 12 nonce + 16 GCM tag)
  to catch accidental plaintext writes.
- Plaintext columns stay in place; application dual-writes to both during
  the transition window.

Phase-2 (future migration, separate deploy):
- Drop plaintext `age`, `sex`, `known_conditions`, `medications`,
  `family_history` columns.
- Switch the repository read path to decrypt from encrypted columns only.

Reversibility: downgrade restores the pre-encryption state by dropping the
encrypted columns. Plaintext data is never removed by this migration, so
rollback is safe without restoring from backup.

Revision ID: 018
Revises: 017
Create Date: 2026-04-24

"""

import base64
import json
import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

revision: str = "018"
down_revision: str | None = "017"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


_ENCRYPTED_COLUMNS: tuple[str, ...] = (
    "age_encrypted",
    "sex_encrypted",
    "known_conditions_encrypted",
    "medications_encrypted",
    "family_history_encrypted",
)


def _encrypt_bytes(plaintext: bytes, key_b64: str) -> bytes:
    key = base64.b64decode(key_b64)
    nonce = os.urandom(12)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, None)


def _encrypt_str(value: str | int | float | None, key_b64: str) -> bytes | None:
    if value is None:
        return None
    return _encrypt_bytes(str(value).encode("utf-8"), key_b64)


def _encrypt_json(value: object | None, key_b64: str) -> bytes | None:
    if value is None:
        return None
    # Empty lists stay as plaintext `[]` → serialize and encrypt the same way
    # so the ciphertext path is a superset of the plaintext one.
    return _encrypt_bytes(json.dumps(value).encode("utf-8"), key_b64)


def upgrade() -> None:
    # 1. Add nullable encrypted columns.
    for col in _ENCRYPTED_COLUMNS:
        op.add_column("user_profiles", sa.Column(col, sa.LargeBinary(), nullable=True))

    # 2. Backfill: read each existing row, encrypt plaintext fields, write ciphertext.
    # Uses ENCRYPTION_KEY from the environment (same key the app uses at runtime).
    key_b64 = os.environ.get("ENCRYPTION_KEY")
    if not key_b64:
        # Migration is running in an env without the key — skip backfill but still
        # leave columns in place. The app's dual-write path will populate them on
        # next profile save; existing profiles won't have PHI encrypted until then.
        # This is a deliberate trade-off to keep migrations self-contained and
        # avoid a hard dependency on application secrets at DDL time.
        return

    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, age, sex, known_conditions, medications, family_history "
            "FROM user_profiles"
        )
    ).fetchall()

    for row in rows:
        conn.execute(
            sa.text(
                "UPDATE user_profiles SET "
                "age_encrypted = :age_enc, "
                "sex_encrypted = :sex_enc, "
                "known_conditions_encrypted = :kc_enc, "
                "medications_encrypted = :meds_enc, "
                "family_history_encrypted = :fh_enc "
                "WHERE id = :id"
            ),
            {
                "id": row.id,
                "age_enc": _encrypt_str(row.age, key_b64),
                "sex_enc": _encrypt_str(row.sex, key_b64),
                # JSONB fields are already lists in Python when read by psycopg2.
                "kc_enc": _encrypt_json(row.known_conditions, key_b64),
                "meds_enc": _encrypt_json(row.medications, key_b64),
                "fh_enc": _encrypt_str(row.family_history, key_b64),
            },
        )

    # 3. CHECK constraints on ciphertext length. 28 bytes = 12 nonce + 16 GCM tag
    # with no payload; any shorter value is mathematically not valid ciphertext.
    # 1 MB upper bound is a sanity cap — real values are << 10 KB.
    for col in _ENCRYPTED_COLUMNS:
        op.create_check_constraint(
            f"ck_user_profiles_{col}_len",
            "user_profiles",
            (
                f"{col} IS NULL OR "
                f"(octet_length({col}) >= 28 AND octet_length({col}) <= 1048576)"
            ),
        )


def downgrade() -> None:
    for col in _ENCRYPTED_COLUMNS:
        op.drop_constraint(f"ck_user_profiles_{col}_len", "user_profiles", type_="check")
        op.drop_column("user_profiles", col)
