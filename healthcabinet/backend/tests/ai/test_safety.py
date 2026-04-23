"""Tests for app/ai/safety.py — safety pipeline functions."""

import pytest

from app.ai.safety import (
    SafetyValidationError,
    inject_disclaimer,
    surface_uncertainty,
    validate_no_diagnostic,
)

_DISCLAIMER_FRAGMENT = "educational purposes only"


@pytest.mark.asyncio
async def test_inject_disclaimer_appends_to_end():
    text = "Your glucose level is within the normal range."
    result = await inject_disclaimer(text)
    # Disclaimer must be the final sentence (after the original text)
    assert result.startswith(text.rstrip())
    assert _DISCLAIMER_FRAGMENT in result
    assert result.index(text.rstrip()) < result.index(_DISCLAIMER_FRAGMENT)


@pytest.mark.asyncio
async def test_inject_disclaimer_strips_trailing_whitespace():
    text = "Your iron is slightly low.   "
    result = await inject_disclaimer(text)
    assert result.startswith("Your iron is slightly low.")


@pytest.mark.asyncio
async def test_validate_no_diagnostic_rejects_diagnosis():
    text = "Based on your results, you have hypothyroidism disease and should seek care."
    with pytest.raises(SafetyValidationError):
        await validate_no_diagnostic(text)


@pytest.mark.asyncio
async def test_validate_no_diagnostic_rejects_diagnosed_with():
    text = "You were diagnosed with anemia."
    with pytest.raises(SafetyValidationError):
        await validate_no_diagnostic(text)


@pytest.mark.asyncio
async def test_validate_no_diagnostic_rejects_consistent_with():
    text = "Your levels are consistent with anemia."
    with pytest.raises(SafetyValidationError):
        await validate_no_diagnostic(text)


@pytest.mark.asyncio
async def test_validate_no_diagnostic_rejects_suggests_disorder():
    text = "This pattern suggests hypothyroidism."
    with pytest.raises(SafetyValidationError):
        await validate_no_diagnostic(text)


@pytest.mark.asyncio
async def test_validate_no_diagnostic_rejects_your_results_show():
    text = "Your results show a clear pattern of vitamin deficiency."
    with pytest.raises(SafetyValidationError):
        await validate_no_diagnostic(text)


@pytest.mark.asyncio
async def test_validate_no_diagnostic_passes_benign_results_show():
    """Benign phrasing like 'your results show a healthy profile' must not be rejected."""
    text = "Your results show values within the expected range."
    result = await validate_no_diagnostic(text)
    assert result == text


@pytest.mark.asyncio
async def test_validate_no_diagnostic_passes_clean_text():
    text = (
        "Your hemoglobin is 13.5 g/dL, which is within the typical reference range. "
        "Your ferritin is slightly below the lower limit of the normal range."
    )
    result = await validate_no_diagnostic(text)
    assert result == text


@pytest.mark.asyncio
async def test_validate_no_diagnostic_passes_disclaimer_text():
    """The disclaimer itself must not trigger safety patterns."""
    from app.ai.safety import _DISCLAIMER

    result = await validate_no_diagnostic(_DISCLAIMER)
    assert result == _DISCLAIMER


@pytest.mark.asyncio
async def test_surface_uncertainty_is_noop():
    text = "Your values look typical."
    result = await surface_uncertainty(text)
    assert result == text


@pytest.mark.asyncio
async def test_surface_uncertainty_passes_values():
    text = "Your values look typical."
    result = await surface_uncertainty(text, values=[])
    assert result == text
