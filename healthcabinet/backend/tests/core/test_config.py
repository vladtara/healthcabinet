import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _base_settings() -> dict[str, object]:
    return {
        "ENVIRONMENT": "test",
        "SECRET_KEY": "test-secret-key-for-unit-tests-only-not-for-production-use-00000000",
        "ENCRYPTION_KEY": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        "DATABASE_URL": "postgresql+asyncpg://healthcabinet:healthcabinet@localhost:5432/test",
        "MINIO_ACCESS_KEY": "minioadmin",
        "MINIO_SECRET_KEY": "minioadmin",
        "BOOTSTRAP_ADMIN_EMAIL": None,
        "BOOTSTRAP_ADMIN_PASSWORD": None,
    }


def test_settings_reject_partial_bootstrap_admin_config() -> None:
    with pytest.raises(ValidationError, match="BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD"):
        Settings(**(_base_settings() | {"BOOTSTRAP_ADMIN_EMAIL": "admin@example.com"}))


def test_settings_reject_short_bootstrap_admin_password() -> None:
    with pytest.raises(ValidationError, match="at least 8 characters"):
        Settings(
            **(
                _base_settings()
                | {
                    "BOOTSTRAP_ADMIN_EMAIL": "admin@example.com",
                    "BOOTSTRAP_ADMIN_PASSWORD": "short",
                }
            )
        )


def test_settings_accept_complete_bootstrap_admin_config() -> None:
    settings = Settings(
        **(
            _base_settings()
            | {
                "BOOTSTRAP_ADMIN_EMAIL": "admin@example.com",
                "BOOTSTRAP_ADMIN_PASSWORD": "bootstrap-pass-123",
            }
        )
    )

    assert str(settings.BOOTSTRAP_ADMIN_EMAIL) == "admin@example.com"
    assert settings.BOOTSTRAP_ADMIN_PASSWORD == "bootstrap-pass-123"
