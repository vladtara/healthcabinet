import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ConditionStr = Annotated[str, StringConstraints(max_length=200)]


class ProfileUpdateRequest(BaseModel):
    age: int | None = Field(None, ge=1, le=120)
    sex: Literal["male", "female", "other", "prefer_not_to_say"] | None = None
    height_cm: float | None = Field(None, ge=50, le=300)
    weight_kg: float | None = Field(None, ge=10, le=500)
    known_conditions: list[ConditionStr] | None = Field(None, max_length=50)
    medications: list[ConditionStr] | None = Field(None, max_length=50)
    family_history: str | None = Field(None, max_length=2000)
    # onboarding_step removed — managed exclusively via PATCH /me/onboarding-step


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    age: int | None
    sex: Literal["male", "female", "other", "prefer_not_to_say"] | None
    height_cm: float | None
    weight_kg: float | None
    known_conditions: list[str]
    medications: list[str]
    family_history: str | None
    onboarding_step: int
    created_at: datetime
    updated_at: datetime


class OnboardingStepRequest(BaseModel):
    step: int = Field(..., ge=1, le=10)


class ConsentLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    consent_type: str
    privacy_policy_version: str
    consented_at: datetime


class ConsentHistoryResponse(BaseModel):
    items: list[ConsentLogResponse]
