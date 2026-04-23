"""014_audit_logs_admin_id_set_null

Make audit_logs.admin_id nullable and change its foreign key from RESTRICT to
SET NULL so admin account deletion preserves audit rows instead of crashing.

Revision ID: 014
Revises: 013
Create Date: 2026-04-16

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: str | None = "013"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("audit_logs", "admin_id", existing_type=sa.UUID(), nullable=True)
    op.drop_constraint("audit_logs_admin_id_fkey", "audit_logs", type_="foreignkey")
    op.create_foreign_key(
        "audit_logs_admin_id_fkey",
        "audit_logs",
        "users",
        ["admin_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM audit_logs WHERE admin_id IS NULL) THEN
                RAISE EXCEPTION
                    'Cannot downgrade migration 014: audit_logs.admin_id contains NULL values';
            END IF;
        END $$;
        """
    )
    op.drop_constraint("audit_logs_admin_id_fkey", "audit_logs", type_="foreignkey")
    op.create_foreign_key(
        "audit_logs_admin_id_fkey",
        "audit_logs",
        "users",
        ["admin_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.alter_column("audit_logs", "admin_id", existing_type=sa.UUID(), nullable=False)
