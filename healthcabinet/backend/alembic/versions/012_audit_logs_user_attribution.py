"""012_audit_logs_user_attribution

Persist audit_logs.user_id so user exports can still recover admin correction
history after the referenced document and health_value rows are deleted.

Revision ID: 012
Revises: 011
Create Date: 2026-04-02

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: str | None = "011"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("user_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_audit_logs_user_id_users",
        "audit_logs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("idx_audit_logs_user_id", "audit_logs", ["user_id"])

    # Best-effort backfill for existing rows while the original references still exist.
    op.execute(
        """
        UPDATE audit_logs AS audit
        SET user_id = documents.user_id
        FROM documents
        WHERE audit.document_id = documents.id
          AND audit.user_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE audit_logs AS audit
        SET user_id = health_values.user_id
        FROM health_values
        WHERE audit.health_value_id = health_values.id
          AND audit.user_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("idx_audit_logs_user_id", table_name="audit_logs")
    op.drop_constraint("fk_audit_logs_user_id_users", "audit_logs", type_="foreignkey")
    op.drop_column("audit_logs", "user_id")
