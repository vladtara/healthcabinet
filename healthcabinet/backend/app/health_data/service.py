"""Business logic for health value retrieval."""

import math
import re
import uuid
from typing import Literal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.documents import repository as document_repository
from app.health_data import repository
from app.health_data.schemas import (
    BaselineSummaryResponse,
    FlagValueResponse,
    HealthValueResponse,
    HealthValueTimelineResponse,
    RecommendationItem,
)
from app.processing.normalizer import canonicalize_biomarker_name
from app.users import repository as user_repository

logger = structlog.get_logger()


def _compute_status(
    value: float,
    ref_low: float | None,
    ref_high: float | None,
) -> Literal["optimal", "borderline", "concerning", "action_needed", "unknown"]:
    """Derive Optimal/Borderline/Concerning/Action needed from reference range."""
    if not math.isfinite(value):
        return "unknown"
    if ref_low is None and ref_high is None:
        return "unknown"
    in_low = ref_low is None or value >= ref_low
    in_high = ref_high is None or value <= ref_high
    if in_low and in_high:
        return "optimal"
    # Two-bound case: percentage deviation from range
    if ref_low is not None and ref_high is not None:
        span = ref_high - ref_low
        if span > 0:
            pct = (ref_low - value) / span if value < ref_low else (value - ref_high) / span
            if pct <= 0.20:
                return "borderline"
            if pct <= 0.50:
                return "concerning"
            return "action_needed"
        # Degenerate range (ref_low == ref_high) — value differs from the single point
        return "borderline"
    # Single-bound case: value is outside the one provided bound
    return "borderline"


def _to_response(record: repository.HealthValueRecord) -> HealthValueResponse:
    return HealthValueResponse(
        id=record.id,
        user_id=record.user_id,
        document_id=record.document_id,
        biomarker_name=record.biomarker_name,
        canonical_biomarker_name=record.canonical_biomarker_name,
        value=record.value,
        unit=record.unit,
        reference_range_low=record.reference_range_low,
        reference_range_high=record.reference_range_high,
        measured_at=record.measured_at,
        confidence=record.confidence,
        needs_review=record.needs_review,
        is_flagged=record.is_flagged,
        flagged_at=record.flagged_at,
        created_at=record.created_at,
        status=_compute_status(
            record.value, record.reference_range_low, record.reference_range_high
        ),
    )


async def list_health_values(
    db: AsyncSession,
    user: User,
    document_kind: repository.DashboardKind | None = None,
) -> list[HealthValueResponse]:
    result = await repository.list_values_by_user(db, user_id=user.id, document_kind=document_kind)
    if result.skipped_corrupt_records:
        logger.warning(
            "health_data.corrupt_rows_skipped",
            user_id=str(user.id),
            skipped_corrupt_records=result.skipped_corrupt_records,
            scope=result.scope,
        )
    return [_to_response(record) for record in result.records]


async def list_health_value_timeline(
    db: AsyncSession,
    user: User,
    canonical_biomarker_name: str,
) -> HealthValueTimelineResponse:
    normalized_name, _ = canonicalize_biomarker_name(canonical_biomarker_name)
    result = await repository.list_timeline_values(
        db,
        user_id=user.id,
        canonical_biomarker_name=normalized_name,
    )
    if result.skipped_corrupt_records:
        logger.warning(
            "health_data.corrupt_rows_skipped",
            user_id=str(user.id),
            skipped_corrupt_records=result.skipped_corrupt_records,
            scope=result.scope,
            canonical_biomarker_name=normalized_name,
        )
    return HealthValueTimelineResponse(
        biomarker_name=canonical_biomarker_name,
        canonical_biomarker_name=normalized_name,
        skipped_corrupt_records=result.skipped_corrupt_records,
        values=[_to_response(record) for record in result.records],
    )


async def flag_health_value(
    db: AsyncSession,
    user: User,
    health_value_id: uuid.UUID,
) -> FlagValueResponse:
    record = await repository.flag_health_value(
        db,
        health_value_id=health_value_id,
        user_id=user.id,
    )
    return FlagValueResponse(
        id=record.id,
        is_flagged=record.is_flagged,
        flagged_at=record.flagged_at,
    )


# ────────────────────────────────────────────────────────────────────────────────
# Story 3.1 — Profile-based baseline recommendations
# ────────────────────────────────────────────────────────────────────────────────

_GENERAL_PANELS: list[tuple[str, str, str]] = [
    # (test_name, rationale, frequency)
    (
        "Complete Blood Count (CBC)",
        "Screens for anemia, infection, and immune system conditions.",
        "Annually",
    ),
    (
        "Comprehensive Metabolic Panel",
        "Checks kidney/liver function, electrolytes, and blood sugar.",
        "Annually",
    ),
    (
        "Lipid Panel",
        "Assesses cardiovascular risk by measuring cholesterol and triglycerides.",
        "Every 1–2 years",
    ),
    (
        "HbA1c",
        "Detects pre-diabetes and diabetes risk over the past 3 months.",
        "Every 3 years",
    ),
    (
        "Vitamin D (25-OH)",
        "Vitamin D deficiency is common and affects bone and immune health.",
        "Annually",
    ),
    (
        "Iron & Ferritin",
        "Iron deficiency is the most common nutritional deficiency worldwide.",
        "Annually",
    ),
    (
        "PSA (Prostate-Specific Antigen)",
        "Early screening discussion for prostate health in men over 50.",
        "Discuss with GP",
    ),
]

_CONDITION_PANELS: list[tuple[list[str], str, str, str]] = [
    # (keywords, test_name, rationale, frequency)
    (
        ["thyroid", "hashimoto", "hypothyroid", "hyperthyroid"],
        "TSH + Free T4 Panel",
        "Monitors thyroid hormone levels to guide treatment and dose adjustments.",
        "Every 6 months",
    ),
    (
        ["diabetes", "pre-diabetes", "prediabetes", "insulin resistance"],
        "HbA1c + Fasting Glucose",
        "Tracks blood sugar control and progression of diabetes or pre-diabetes.",
        "Every 3 months",
    ),
    (
        ["hypertension", "high blood pressure", "blood pressure"],
        "Comprehensive Metabolic Panel",
        "Monitors kidney function and electrolytes affected by hypertension.",
        "Every 6 months",
    ),
    (
        ["cholesterol", "hyperlipidemia", "hyperlipid", "dyslipidemia"],
        "Lipid Panel",
        "Tracks response to lifestyle changes or medication for cholesterol management.",
        "Every 3 months",
    ),
    (
        ["anemia", "iron deficiency"],
        "CBC + Iron + Ferritin + B12",
        "Comprehensive anemia workup to determine type and guide treatment.",
        "Every 6 months",
    ),
    (
        ["vitamin d deficiency", "vitamin d", "osteoporosis", "osteopenia"],
        "Vitamin D (25-OH)",
        "Tracks supplementation response and bone health status.",
        "Every 6 months",
    ),
    (
        ["celiac", "celiac disease", "gluten intolerance"],
        "tTG-IgA Antibodies",
        "Monitors celiac disease activity and adherence to a gluten-free diet.",
        "Annually",
    ),
    (
        ["pcos", "polycystic ovary", "polycystic ovarian"],
        "Testosterone + FSH/LH Panel",
        "Tracks hormonal imbalances associated with PCOS.",
        "Every 6 months",
    ),
]

_MIN_RECS = 3
_MAX_RECS = 5


def _generate_baseline_recommendations(
    age: int | None,
    sex: str | None,
    known_conditions: list[str],
) -> list[RecommendationItem]:
    """Derive 3–5 health test recommendations from profile data only.

    No health_values DB queries are made. Output is deterministic and
    informational — not diagnostic advice.
    """
    condition_items: list[RecommendationItem] = []
    condition_names_added: set[str] = set()

    # P4: strip empty/whitespace entries; P1: compile word-boundary patterns per keyword
    conditions_lower = [c.lower() for c in known_conditions if c and c.strip()]

    for keywords, test_name, rationale, frequency in _CONDITION_PANELS:
        if test_name in condition_names_added:
            continue
        # P1: word-boundary matching prevents "thyroid" matching "parathyroid"
        if any(
            re.search(rf"\b{re.escape(kw)}\b", cond) for kw in keywords for cond in conditions_lower
        ):
            condition_items.append(
                RecommendationItem(
                    test_name=test_name,
                    rationale=rationale,
                    frequency=frequency,
                    category="condition_specific",
                )
            )
            condition_names_added.add(test_name)

    # P5: normalize sex to lowercase once for all comparisons below
    sex_lower = sex.lower() if sex is not None else None

    general_items: list[RecommendationItem] = []
    for test_name, rationale, frequency in _GENERAL_PANELS:
        if test_name in condition_names_added:
            continue
        # Skip if a condition-specific test already covers this general test
        # (e.g., skip general "HbA1c" when "HbA1c + Fasting Glucose" is present)
        if any(test_name in cond_name for cond_name in condition_names_added):
            continue
        # Age/sex gates
        if test_name == "HbA1c" and (age is None or age < 40):
            continue
        if test_name == "PSA (Prostate-Specific Antigen)" and (
            sex_lower != "male" or (age is not None and age < 50)
        ):
            continue
        if test_name == "Vitamin D (25-OH)" and (age is None or age < 60):
            continue
        if test_name == "Iron & Ferritin" and sex_lower not in (None, "female"):
            continue
        # P3: redundant guard removed — already covered by `if test_name in condition_names_added`
        general_items.append(
            RecommendationItem(
                test_name=test_name,
                rationale=rationale,
                frequency=frequency,
                category="general",
            )
        )

    combined = condition_items + general_items
    combined = combined[:_MAX_RECS]

    # Ensure minimum of 3 by re-adding unconditional generals if needed
    if len(combined) < _MIN_RECS:
        fallback_names = {r.test_name for r in combined}
        for test_name, rationale, frequency in _GENERAL_PANELS:
            if len(combined) >= _MIN_RECS:
                break
            if test_name not in fallback_names:
                combined.append(
                    RecommendationItem(
                        test_name=test_name,
                        rationale=rationale,
                        frequency=frequency,
                        category="general",
                    )
                )
                fallback_names.add(test_name)

    return combined


async def get_dashboard_baseline(db: AsyncSession, user: User) -> BaselineSummaryResponse:
    """Return profile-based baseline recommendations for the empty-state dashboard.

    Derives recommendations from user profile data only — no health_values query.
    """
    profile = await user_repository.get_user_profile(db, user.id)
    age = profile.age if profile is not None else None
    sex = profile.sex if profile is not None else None
    known_conditions = (profile.known_conditions or []) if profile is not None else []

    recommendations = _generate_baseline_recommendations(age, sex, known_conditions)
    has_uploads = await document_repository.has_user_documents(db, user.id)
    return BaselineSummaryResponse(recommendations=recommendations, has_uploads=has_uploads)
