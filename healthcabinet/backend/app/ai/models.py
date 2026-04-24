import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, LargeBinary, String, func
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
