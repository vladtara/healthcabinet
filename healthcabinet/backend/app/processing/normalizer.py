"""Pure normalization helpers for extracted health values."""

from app.processing.schemas import ExtractedHealthValue, ExtractionResult, NormalizedHealthValue

_CONFIDENCE_THRESHOLD = 0.7

_BIOMARKER_ALIASES: dict[str, str] = {
    "glucose": "glucose",
    "blood glucose": "glucose",
    "fasting glucose": "glucose",
    "hemoglobin": "hemoglobin",
    "haemoglobin": "hemoglobin",
    "hgb": "hemoglobin",
    "cholesterol": "cholesterol_total",
    "total cholesterol": "cholesterol_total",
    "hdl": "cholesterol_hdl",
    "hdl cholesterol": "cholesterol_hdl",
    "ldl": "cholesterol_ldl",
    "ldl cholesterol": "cholesterol_ldl",
    "triglycerides": "triglycerides",
    "vitamin d": "vitamin_d",
    "vitamin d3": "vitamin_d",
    "25-oh vitamin d": "vitamin_d",
    "tsh": "tsh",
    "thyroid stimulating hormone": "tsh",
    "hb1ac": "hba1c",
    "hba1c": "hba1c",
    "hemoglobin a1c": "hba1c",
    "creatinine": "creatinine",
    "alt": "alt",
    "ast": "ast",
}

_UNIT_ALIASES: dict[str, str] = {
    "mg/dl": "mg/dL",
    "mmol/l": "mmol/L",
    "g/dl": "g/dL",
    "iu/l": "IU/L",
    "u/l": "U/L",
    "µiu/ml": "uIU/mL",
    "miu/l": "mIU/L",
    "%": "%",
}


def _clean_token(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def canonicalize_biomarker_name(name: str) -> tuple[str, bool]:
    cleaned = _clean_token(name)
    canonical = _BIOMARKER_ALIASES.get(cleaned)
    if canonical is not None:
        return canonical, True
    return cleaned.replace(" ", "_"), False


def normalize_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    cleaned = unit.strip()
    if not cleaned:
        return None
    return _UNIT_ALIASES.get(cleaned.lower(), cleaned)


def _convert_value(value: float, unit: str | None) -> tuple[float, str | None, float]:
    normalized_unit = normalize_unit(unit)
    if normalized_unit == "mg/L":
        return value / 10.0, "mg/dL", 0.9
    if normalized_unit == "g/L":
        return value / 10.0, "g/dL", 0.9
    return value, normalized_unit, 1.0


def _convert_reference_range(
    reference_range: float | None,
    unit: str | None,
) -> float | None:
    if reference_range is None:
        return None
    converted_value, _, _ = _convert_value(reference_range, unit)
    return converted_value


def normalize_health_value(value: ExtractedHealthValue) -> NormalizedHealthValue:
    canonical_name, matched_alias = canonicalize_biomarker_name(value.biomarker_name)
    normalized_value, normalized_unit, conversion_confidence = _convert_value(
        value.value, value.unit
    )

    confidence = min(value.confidence, conversion_confidence)
    if not matched_alias:
        confidence = min(confidence, 0.85)

    needs_review = confidence < _CONFIDENCE_THRESHOLD

    return NormalizedHealthValue(
        biomarker_name=value.biomarker_name.strip(),
        canonical_biomarker_name=canonical_name,
        value=normalized_value,
        unit=normalized_unit,
        reference_range_low=_convert_reference_range(value.reference_range_low, value.unit),
        reference_range_high=_convert_reference_range(value.reference_range_high, value.unit),
        confidence=confidence,
        needs_review=needs_review,
    )


def normalize_extraction_result(result: ExtractionResult) -> list[NormalizedHealthValue]:
    return [normalize_health_value(value) for value in result.values]
