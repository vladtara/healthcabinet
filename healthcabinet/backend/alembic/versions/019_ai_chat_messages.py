"""ai_chat_messages

Persistent per-thread chat history for the AI assistant.

Each row is one turn (user question or assistant reply) within a thread.
`thread_id` is derived server-side:
  - document-scoped chat: `doc:{user_id}:{document_id}`
  - dashboard-scoped chat: `dash:{user_id}:{document_kind}`

`text_encrypted` holds the AES-256-GCM ciphertext (nonce + GCM tag + body),
same format as `ai_memories.interpretation_encrypted`.

`role` is a free-form text column constrained to {'user','assistant'} via a
CHECK. System / tool-call messages are not stored here; the prompt builder
synthesizes them on demand from profile + main summary + filter view.

Revision ID: 019
Revises: 018
Create Date: 2026-04-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "019"
down_revision: str | None = "018"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("thread_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("text_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_ai_chat_messages_role"),
        sa.CheckConstraint(
            "octet_length(text_encrypted) >= 28 AND octet_length(text_encrypted) <= 1048576",
            name="ck_ai_chat_messages_text_encrypted_len",
        ),
    )
    op.create_index(
        "idx_ai_chat_messages_thread",
        "ai_chat_messages",
        ["user_id", "thread_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_ai_chat_messages_thread", table_name="ai_chat_messages")
    op.drop_table("ai_chat_messages")
