import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Document(Base):
    """Document model. s3_key is stored AES-256-GCM encrypted in repository.py."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    s3_key_encrypted: Mapped[bytes | None] = mapped_column(nullable=True)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    arq_job_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    keep_partial: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Document intelligence metadata (Story 15.2)
    # document_kind is one of: "analysis" | "document" | "unknown".
    # "unknown" is the safe default for new/untriaged rows; the processing pipeline
    # reclassifies once persisted extraction state is authoritative.
    document_kind: Mapped[str] = mapped_column(String, nullable=False, default="unknown")
    # needs_date_confirmation is True when extraction produced a yearless date.
    # The owner must call POST /documents/{id}/confirm-date-year to resolve it.
    needs_date_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # partial_measured_at_text is the raw source fragment (e.g. "12.03" or "12 Mar")
    # recovered from the document when the year cannot be inferred by the extractor.
    # Cleared once the user confirms the year.
    partial_measured_at_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Pending retry metadata — set at /reupload-url, moved to authoritative at /notify.
    # Ensures authoritative fields stay consistent with the current extracted values
    # even if the client never completes the PUT or never calls /notify.
    pending_s3_key_encrypted: Mapped[bytes | None] = mapped_column(nullable=True)
    pending_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    pending_file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    pending_file_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_documents_user_id", "user_id"),
        Index("idx_documents_status", "status"),
    )
