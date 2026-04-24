"""ai_memory_scope

Add a `scope` column to `ai_memories` so the same table can hold the
per-user aggregate ("overall") clinical note alongside per-document rows.
`scope` is NULL for per-document rows (today's behaviour) and set to a
string like "overall_all" for the dashboard-level aggregate.

A partial unique index on (user_id, scope) WHERE scope IS NOT NULL
enforces "at most one aggregate row per scope per user". Per-document
uniqueness continues to be enforced by `uq_ai_memories_user_document`
from revision 009.

Revision ID: 017
Revises: 016
Create Date: 2026-04-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "017"
down_revision: str | None = "016"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_memories",
        sa.Column("scope", sa.String(length=32), nullable=True),
    )
    op.create_index(
        "uq_ai_memories_user_scope",
        "ai_memories",
        ["user_id", "scope"],
        unique=True,
        postgresql_where=sa.text("scope IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_ai_memories_user_scope", table_name="ai_memories")
    op.drop_column("ai_memories", "scope")
