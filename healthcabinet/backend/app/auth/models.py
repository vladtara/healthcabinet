import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="user")  # 'user' | 'admin'
    tier: Mapped[str] = mapped_column(String, nullable=False, default="free")  # 'free' | 'paid'
    account_status: Mapped[str] = mapped_column(
        String, nullable=False, server_default="active", default="active"
    )  # 'active' | 'suspended'
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Any access/refresh token whose `iat` is strictly before this instant is treated as
    # revoked. Admins bump this via POST /admin/users/{id}/revoke-sessions to force-logout
    # a user without suspending the account. NULL means no revocation has ever occurred.
    tokens_invalid_before: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # NOTE: onupdate=func.now() emits the SQL expression but with expire_on_commit=False
    # the in-memory value is NOT refreshed after ORM UPDATE. Callers must do
    # `await session.refresh(obj)` to get the current updated_at after a write.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("idx_users_account_status", "account_status"),)
