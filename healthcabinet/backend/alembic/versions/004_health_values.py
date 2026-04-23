"""health_values

Revision ID: 004
Revises: 003
Create Date: 2026-03-23

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "health_values",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
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
            nullable=False,
        ),
        sa.Column("biomarker_name", sa.Text(), nullable=False),
        sa.Column("canonical_biomarker_name", sa.Text(), nullable=False),
        sa.Column("value_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("reference_range_low", sa.Numeric(), nullable=True),
        sa.Column("reference_range_high", sa.Numeric(), nullable=True),
        sa.Column("measured_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    op.create_index("idx_health_values_user_id", "health_values", ["user_id"])
    op.create_index("idx_health_values_document_id", "health_values", ["document_id"])
    op.create_index(
        "idx_health_values_user_biomarker",
        "health_values",
        ["user_id", "canonical_biomarker_name"],
    )


def downgrade() -> None:
    op.drop_index("idx_health_values_user_biomarker", table_name="health_values")
    op.drop_index("idx_health_values_document_id", table_name="health_values")
    op.drop_index("idx_health_values_user_id", table_name="health_values")
    op.drop_table("health_values")
