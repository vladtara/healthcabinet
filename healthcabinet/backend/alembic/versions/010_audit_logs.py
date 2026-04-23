"""010_audit_logs

Create audit_logs table for admin value corrections and add indexes on
health_values.is_flagged and health_values.confidence (Epic 4 retro action item A4).

Revision ID: 010
Revises: 009
Create Date: 2026-04-01

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: str | None = "009"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "admin_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.UUID(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "health_value_id",
            sa.UUID(),
            sa.ForeignKey("health_values.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("value_name", sa.Text(), nullable=False),
        sa.Column("original_value", sa.Text(), nullable=False),
        sa.Column("new_value", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "corrected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for audit_logs
    op.create_index("idx_audit_logs_admin_id", "audit_logs", ["admin_id"])
    op.create_index("idx_audit_logs_document_id", "audit_logs", ["document_id"])
    op.create_index("idx_audit_logs_health_value_id", "audit_logs", ["health_value_id"])

    # Index on health_values.is_flagged (Epic 4 retro action item A4)
    op.create_index("idx_health_values_is_flagged", "health_values", ["is_flagged"])

    # Index on health_values.confidence for < 0.7 queue filter
    op.create_index("idx_health_values_confidence", "health_values", ["confidence"])


def downgrade() -> None:
    op.drop_index("idx_health_values_confidence", table_name="health_values")
    op.drop_index("idx_health_values_is_flagged", table_name="health_values")
    op.drop_index("idx_audit_logs_health_value_id", table_name="audit_logs")
    op.drop_index("idx_audit_logs_document_id", table_name="audit_logs")
    op.drop_index("idx_audit_logs_admin_id", table_name="audit_logs")
    op.drop_table("audit_logs")
