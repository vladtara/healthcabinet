from typing import Literal

from pydantic import EmailStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    ENVIRONMENT: str = "development"
    SECRET_KEY: str

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_min_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters. "
                "HS256 with a short key is trivially brute-forceable offline."
            )
        return v

    ENCRYPTION_KEY: str  # base64-encoded 32-byte key
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]  # override in production

    # Refresh-cookie flags. Defaults are production-safe (HTTPS + Strict).
    # Dev over plain HTTP must set COOKIE_SECURE=false — browsers drop
    # `Secure` cookies on non-secure origins (localhost is a Chrome-only
    # exemption and fails on 127.0.0.1, Docker IPs, and some preview hosts).
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: Literal["strict", "lax", "none"] = "strict"

    # Database
    DATABASE_URL: str  # postgresql+asyncpg://...

    # AWS (eu-central-1 only)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "eu-central-1"
    AWS_S3_BUCKET: str = ""

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    AI_CHAT_MODEL: str = "claude-sonnet-4-6"
    ANTHROPIC_EXTRACTION_MODEL: str = "claude-sonnet-4-20250514"

    # Sentry
    SENTRY_DSN: str = ""

    # LangSmith / tracing
    LANGSMITH_TRACING: bool = False
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "healthcabinet"

    # Document processing
    DOCUMENT_PROCESSING_MAX_BYTES: int = 20 * 1024 * 1024

    # MinIO (S3-compatible object storage)
    MINIO_ENDPOINT: str = "minio:9000"  # host:port only; scheme is derived from MINIO_SECURE
    MINIO_ACCESS_KEY: str  # no default — must be set explicitly; fail loudly if absent
    MINIO_SECRET_KEY: str  # no default — must be set explicitly; fail loudly if absent
    MINIO_BUCKET: str = "healthcabinet"
    MINIO_SECURE: bool = False  # True in production (HTTPS); controls endpoint scheme

    # Runtime / deployment
    RUN_DB_MIGRATIONS_ON_STARTUP: bool = False
    BOOTSTRAP_ADMIN_EMAIL: EmailStr | None = None
    BOOTSTRAP_ADMIN_PASSWORD: str | None = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Token expiry
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Proxy / Rate limiting
    # Comma-separated trusted proxy IPs or CIDR ranges for ProxyHeadersMiddleware.
    # Use "*" (default) in development or when the proxy infrastructure is not fixed.
    # In production, set to your load balancer's IP(s) or VPC CIDR to prevent clients
    # from forging X-Forwarded-For and bypassing per-IP rate limiting.
    TRUSTED_PROXY_IPS: str = "*"

    # Legal
    PRIVACY_POLICY_VERSION: str = "1.0"

    @model_validator(mode="after")
    def validate_cookie_flags(self) -> "Settings":
        # SameSite=None requires Secure per modern browser rules; the combination
        # SameSite=None + Secure=False is silently dropped by Chrome/Firefox.
        if self.COOKIE_SAMESITE == "none" and not self.COOKIE_SECURE:
            raise ValueError("COOKIE_SAMESITE='none' requires COOKIE_SECURE=true")
        return self

    @model_validator(mode="after")
    def validate_bootstrap_admin(self) -> "Settings":
        email = self.BOOTSTRAP_ADMIN_EMAIL
        password = self.BOOTSTRAP_ADMIN_PASSWORD
        if (email is None) != (password is None):
            raise ValueError(
                "BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD must be set together"
            )
        if password is None:
            return self
        if len(password) < 8:
            raise ValueError("BOOTSTRAP_ADMIN_PASSWORD must be at least 8 characters")
        if len(password.encode("utf-8")) > 72:
            raise ValueError("BOOTSTRAP_ADMIN_PASSWORD must not exceed 72 bytes (bcrypt limit)")
        return self


settings = Settings()  # type: ignore[call-arg]
