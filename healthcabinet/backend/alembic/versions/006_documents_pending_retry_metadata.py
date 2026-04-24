"""documents_pending_retry_metadata

Adds pending_* columns to the documents table to stage retry file metadata without
overwriting authoritative fields until the replacement upload is confirmed via /notify.

This defers the metadata swap to when the file has actually been PUT to MinIO,
keeping extracted health values consistent with the visible filename/s3_key at all times.

Revision ID: 006
Revises: 005
Create Date: 2026-03-25

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: str | None = "005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents", sa.Column("pending_s3_key_encrypted", sa.LargeBinary(), nullable=True)
    )
    op.add_column("documents", sa.Column("pending_filename", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("pending_file_size_bytes", sa.BigInteger(), nullable=True))
    op.add_column("documents", sa.Column("pending_file_type", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "pending_file_type")
    op.drop_column("documents", "pending_file_size_bytes")
    op.drop_column("documents", "pending_filename")
    op.drop_column("documents", "pending_s3_key_encrypted")
