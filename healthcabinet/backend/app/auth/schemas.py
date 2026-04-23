from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


def _validate_password_bytes(v: str) -> str:
    """Reject passwords exceeding bcrypt's 72-byte silent truncation limit.

    Shared by LoginRequest and RegisterRequest to ensure a single source of truth
    for the bcrypt byte cap — update this one function if the limit ever changes.
    """
    if len(v.encode("utf-8")) > 72:
        raise ValueError("password must not exceed 72 bytes (bcrypt limit)")
    return v


class LoginRequest(BaseModel):
    email: EmailStr
    # min_length=1 rejects empty strings at the schema layer before bcrypt is invoked.
    # Intentionally diverges from RegisterRequest.password (min_length=8): login validates
    # against an already-stored hash — the 8-char creation requirement is not re-enforced
    # at login time (the stored hash is the authority). This divergence is visible in
    # OpenAPI docs and is by design.
    password: Annotated[str, Field(min_length=1)]

    @field_validator("password")
    @classmethod
    def password_max_bytes(cls, v: str) -> str:
        return _validate_password_bytes(v)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: EmailStr
    # min_length/max_length count Unicode characters; the validator below enforces the
    # bcrypt 72-byte limit at the UTF-8 byte level to prevent silent truncation for
    # non-ASCII passwords (e.g. 25 × "あ" = 75 bytes but only 25 chars).
    password: Annotated[str, Field(min_length=8)]
    gdpr_consent: Literal[True]
    privacy_policy_version: Annotated[str, Field(min_length=1)]

    @field_validator("password")
    @classmethod
    def password_max_bytes(cls, v: str) -> str:
        return _validate_password_bytes(v)


class RegisterResponse(BaseModel):
    id: UUID
    email: str
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: str
    email: str
    role: str
    tier: str
