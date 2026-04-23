"""ai_memories_epic4

Creates the ai_memories table (the SQLAlchemy model existed previously but
no migration was ever written for it) and adds the Epic 4 columns:
document_id (FK to documents), interpretation_encrypted (AES-256-GCM blob),
model_version (tracking which Claude model produced the interpretation), and
safety_validated (boolean flag confirming the safety pipeline ran successfully).

Revision ID: 008
Revises: 007
Create Date: 2026-03-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: str | None = "007"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("context_json_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("interpretation_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column(
            "safety_validated",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ai_memories_document_id", "ai_memories", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_memories_document_id", table_name="ai_memories")
    op.drop_table("ai_memories")
