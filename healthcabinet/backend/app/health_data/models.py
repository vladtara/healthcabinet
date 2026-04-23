import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HealthValue(Base):
    """Immutable extracted health data row with repository-layer value encryption."""

    __tablename__ = "health_values"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    biomarker_name: Mapped[str] = mapped_column(String, nullable=False)
    canonical_biomarker_name: Mapped[str] = mapped_column(String, nullable=False)
    value_encrypted: Mapped[bytes] = mapped_column(nullable=False)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    reference_range_low: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    reference_range_high: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    measured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_flagged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    flagged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Flag review state — separate from is_flagged. Reviewed flags stay flagged historically.
    flag_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    flag_reviewed_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_health_values_user_id", "user_id"),
        Index("idx_health_values_document_id", "document_id"),
        Index("idx_health_values_user_biomarker", "user_id", "canonical_biomarker_name"),
        Index("idx_health_values_flag_review", "is_flagged", "flag_reviewed_at"),
    )
