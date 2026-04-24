import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ConsentLog(Base):
    __tablename__ = "consent_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    consent_type: Mapped[str] = mapped_column(String, nullable=False)  # 'health_data_processing'
    privacy_policy_version: Mapped[str] = mapped_column(String, nullable=False)
    consented_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("idx_consent_logs_user_id", "user_id"),)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str | None] = mapped_column(Text, nullable=True)
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    known_conditions: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    medications: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    family_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    # AES-256-GCM ciphertext columns (phase-1 of the encryption migration).
    # Populated alongside the plaintext columns above on every upsert. Phase-2
    # drops the plaintext columns and switches reads to these.
    age_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    sex_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    known_conditions_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    medications_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    family_history_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    onboarding_step: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("idx_user_profiles_user_id", "user_id"),)
