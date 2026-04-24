import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AiMemory(Base):
    """AI memory/context per user, per document. Interpretation encrypted at rest."""

    __tablename__ = "ai_memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    context_json_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    interpretation_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # NULL for per-document rows; set to "overall_all" (or a future per-filter
    # variant) when the row represents a user-level aggregate note instead of
    # a per-document interpretation.
    scope: Mapped[str | None] = mapped_column(String(32), nullable=True)
    safety_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AiChatMessage(Base):
    """One turn (user question or assistant reply) in an AI chat thread.

    thread_id is derived server-side from (user_id, document_id) for
    per-document chat or (user_id, document_kind) for dashboard chat. The
    client never supplies it.

    text_encrypted is AES-256-GCM ciphertext (same format as ai_memories.
    interpretation_encrypted). Decryption happens only in repository.py.
    """

    __tablename__ = "ai_chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    thread_id: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)  # 'user' | 'assistant'
    text_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_ai_chat_messages_role"),
        Index("idx_ai_chat_messages_thread", "user_id", "thread_id", "created_at"),
    )
