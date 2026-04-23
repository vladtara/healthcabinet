"""011_admin_user_account_state_and_flag_review

Add users.account_status, users.last_login_at for admin user management.
Add health_values.flag_reviewed_at, health_values.flag_reviewed_by_admin_id
for flag review state (separate from user-facing is_flagged).

Revision ID: 011
Revises: 010
Create Date: 2026-04-01

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: str | None = "010"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # -- users table --
    op.add_column(
        "users",
        sa.Column("account_status", sa.String(), nullable=False, server_default="active"),
    )
    op.add_column(
        "users",
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_users_account_status", "users", ["account_status"])

    # -- health_values table --
    op.add_column(
        "health_values",
        sa.Column("flag_reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "health_values",
        sa.Column(
            "flag_reviewed_by_admin_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_health_values_flag_review",
        "health_values",
        ["is_flagged", "flag_reviewed_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_health_values_flag_review", table_name="health_values")
    op.drop_column("health_values", "flag_reviewed_by_admin_id")
    op.drop_column("health_values", "flag_reviewed_at")
    op.drop_index("idx_users_account_status", table_name="users")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "account_status")
