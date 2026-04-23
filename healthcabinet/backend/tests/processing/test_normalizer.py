"""Unit tests for extraction normalization helpers."""

from app.processing.normalizer import normalize_extraction_result, normalize_health_value
from app.processing.schemas import ExtractedHealthValue, ExtractionResult


def test_normalize_health_value_canonicalizes_name_and_unit():
    value = ExtractedHealthValue(
        biomarker_name="Blood Glucose",
        value=95.0,
        unit="mg/dl",
        reference_range_low=70.0,
        reference_range_high=99.0,
        confidence=0.95,
    )

    normalized = normalize_health_value(value)

    assert normalized.canonical_biomarker_name == "glucose"
    assert normalized.unit == "mg/dL"
    assert normalized.confidence == 0.95
    assert normalized.needs_review is False


def test_normalize_extraction_result_reduces_confidence_for_unknown_alias():
    result = ExtractionResult(
        values=[
            ExtractedHealthValue(
                biomarker_name="Unmapped Marker",
                value=1.2,
                unit=None,
                reference_range_low=None,
                reference_range_high=None,
                confidence=0.9,
            )
        ]
    )

    normalized = normalize_extraction_result(result)

    assert normalized[0].canonical_biomarker_name == "unmapped_marker"
    assert normalized[0].confidence == 0.85


def test_normalize_health_value_converts_reference_ranges_with_unit_conversion():
    value = ExtractedHealthValue(
        biomarker_name="Glucose",
        value=950.0,
        unit="mg/L",
        reference_range_low=700.0,
        reference_range_high=990.0,
        confidence=0.95,
    )

    normalized = normalize_health_value(value)

    assert normalized.value == 95.0
    assert normalized.unit == "mg/dL"
    assert normalized.reference_range_low == 70.0
    assert normalized.reference_range_high == 99.0
