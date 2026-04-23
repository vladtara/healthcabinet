"""013_consent_logs_retain_on_user_delete

Change consent_logs.user_id FK from CASCADE to SET NULL so consent records
are retained when a user deletes their account (GDPR regulatory requirement).

Revision ID: 013
Revises: 012
Create Date: 2026-04-05

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Make user_id nullable so it can be SET NULL on user deletion
    op.alter_column("consent_logs", "user_id", existing_type=sa.UUID(), nullable=True)

    # Drop the existing CASCADE FK and recreate with SET NULL
    op.drop_constraint("consent_logs_user_id_fkey", "consent_logs", type_="foreignkey")
    op.create_foreign_key(
        "consent_logs_user_id_fkey",
        "consent_logs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Delete orphaned consent_logs with NULL user_id before restoring NOT NULL constraint
    op.execute("DELETE FROM consent_logs WHERE user_id IS NULL")
    op.drop_constraint("consent_logs_user_id_fkey", "consent_logs", type_="foreignkey")
    op.create_foreign_key(
        "consent_logs_user_id_fkey",
        "consent_logs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column("consent_logs", "user_id", existing_type=sa.UUID(), nullable=False)
