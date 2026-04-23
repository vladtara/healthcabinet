"""015_users_tokens_invalid_before

Add users.tokens_invalid_before for admin-initiated session revocation.
Any JWT (access or refresh) with iat strictly before this timestamp is rejected
at token validation time, effectively force-logging-out the user on all devices.
NULL (the default) means no revocation has ever been performed.

Revision ID: 015
Revises: 014
Create Date: 2026-04-18

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "015"
down_revision: str | None = "014"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("tokens_invalid_before", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "tokens_invalid_before")
