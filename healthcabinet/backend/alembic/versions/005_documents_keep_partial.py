"""documents_keep_partial

Adds keep_partial nullable boolean to documents table to persist prompt-dismissal
for partial extraction results (Story 2.5).

Revision ID: 005
Revises: 004
Create Date: 2026-03-24

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: str | None = "004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("keep_partial", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "keep_partial")
