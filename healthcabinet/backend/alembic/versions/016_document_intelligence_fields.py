"""016_document_intelligence_fields

Add document intelligence columns to the `documents` table (Story 15.2):

- `document_kind`: literal classification persisted alongside status
  ("analysis" | "document" | "unknown"). Backfilled from persisted health
  values and the existing upload/processing status for legacy rows.
- `needs_date_confirmation`: boolean gate for the year-confirmation flow.
  Legacy rows default to `false` because the raw extraction fragment is not
  stored today, so backfilling missing-year state would be fiction.
- `partial_measured_at_text`: raw day/month fragment recovered at extraction
  time when the extractor could not determine a year. Nullable; never
  backfilled for legacy rows.

Classification backfill (conservative):
- documents with >= 1 health_values row                        => "analysis"
- documents with 0 health_values and status in (completed,partial) => "document"
- documents with status = "failed"                              => "unknown"
- all other rows default to "unknown" via the column default.

Revision ID: 016
Revises: 015
Create Date: 2026-04-19

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "016"
down_revision: str | None = "015"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Add columns with server defaults so the ALTER is safe on large tables
    # and existing rows pick up deterministic defaults before we backfill.
    op.add_column(
        "documents",
        sa.Column(
            "document_kind",
            sa.String(),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "needs_date_confirmation",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "documents",
        sa.Column("partial_measured_at_text", sa.Text(), nullable=True),
    )

    # Backfill document_kind from persisted extraction state (AC 6).
    # Order matters: set "analysis" for documents with health values first,
    # then "document" for successful processing with no values, then "unknown"
    # for failed cases. The remaining rows (pending/processing) keep the
    # "unknown" default, which is safe because they have not terminated yet.
    op.execute(
        """
        UPDATE documents
           SET document_kind = 'analysis'
         WHERE id IN (
               SELECT DISTINCT document_id FROM health_values
         );
        """
    )
    op.execute(
        """
        UPDATE documents
           SET document_kind = 'document'
         WHERE document_kind = 'unknown'
           AND status IN ('completed', 'partial')
           AND id NOT IN (
               SELECT DISTINCT document_id FROM health_values
         );
        """
    )
    # Guard: the first UPDATE above set document_kind='analysis' for any row
    # with persisted health_values. A failed row that somehow has persisted
    # values should KEEP 'analysis' because the rows are the authoritative
    # signal, not the status. Exclude those rows from the failed -> unknown
    # backfill to avoid overwriting a correct classification.
    op.execute(
        """
        UPDATE documents
           SET document_kind = 'unknown'
         WHERE status = 'failed'
           AND id NOT IN (
               SELECT DISTINCT document_id FROM health_values
         );
        """
    )

    # Drop server defaults now that legacy rows are deterministic; application
    # code owns the default from here on via SQLAlchemy model defaults.
    op.alter_column("documents", "document_kind", server_default=None)
    op.alter_column("documents", "needs_date_confirmation", server_default=None)


def downgrade() -> None:
    op.drop_column("documents", "partial_measured_at_text")
    op.drop_column("documents", "needs_date_confirmation")
    op.drop_column("documents", "document_kind")
