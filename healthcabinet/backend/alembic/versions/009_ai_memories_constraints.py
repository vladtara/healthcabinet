"""ai_memories_constraints

Add UNIQUE constraint on (user_id, document_id) and a composite index
on (user_id, document_id) to ai_memories. The UNIQUE constraint prevents
duplicate interpretations on document reprocessing (which would cause
scalar_one_or_none to raise MultipleResultsFound). The composite index
speeds up all ownership-filtered queries.

Revision ID: 009
Revises: 008
Create Date: 2026-03-26

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: str | None = "008"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_ai_memories_user_document",
        "ai_memories",
        ["user_id", "document_id"],
    )
    op.create_unique_constraint(
        "uq_ai_memories_user_document",
        "ai_memories",
        ["user_id", "document_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_ai_memories_user_document", "ai_memories", type_="unique")
    op.drop_index("ix_ai_memories_user_document", table_name="ai_memories")
