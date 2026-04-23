"""health_values_flagging

Adds is_flagged and flagged_at columns to the health_values table to support
user-submitted extraction-error signals for the future admin review queue
(Epic 5 Story 5.2: extraction-error-queue-manual-value-correction).

Backfills existing rows with is_flagged=false so the NOT NULL constraint is safe.

Revision ID: 007
Revises: 006
Create Date: 2026-03-25

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: str | None = "006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Use a server default so existing rows read as false immediately and new inserts stay safe.
    op.add_column(
        "health_values",
        sa.Column(
            "is_flagged",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "health_values",
        sa.Column("flagged_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("health_values", "flagged_at")
    op.drop_column("health_values", "is_flagged")
