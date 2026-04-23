"""AI safety pipeline for health interpretation outputs."""

import re
from collections.abc import Sequence


class SafetyValidationError(Exception):
    pass


# AC1 spec order: inject_disclaimer → validate_no_diagnostic → surface_uncertainty.
# We validate BEFORE injecting the disclaimer so that we check only the raw AI
# output — the disclaimer text itself does not trigger any pattern.
# service.py therefore calls: validate_no_diagnostic → surface_uncertainty →
# inject_disclaimer (functionally equivalent to spec because the disclaimer is
# pattern-safe, and more robust against future pattern changes).

_FORBIDDEN_PATTERNS = [
    # Explicit diagnosis statements
    r"\byou have\b.*\b(disease|disorder|syndrome|condition)\b",
    r"\bdiagnosed with\b",
    # Prescription/medication instructions
    r"\btake\b.*\b(mg|mcg|units)\b",
    r"\bprescrib",
    r"\byou should (start|stop|take|avoid)\b",
    # Implicit diagnoses via hedged phrasing
    r"\bconsistent with\b.*\b(disease|disorder|syndrome|condition|anemia|diabetes|hypothyroidism|hyperthyroidism|cancer|deficiency)\b",
    r"\b(suggests?|indicates?)\b.*\b(disease|disorder|syndrome|condition|anemia|diabetes|hypothyroidism|hyperthyroidism|cancer|deficiency)\b",
    # "your results show/indicate/suggest" + medical condition (avoids blocking benign
    # phrasing like "your results show a healthy profile")
    r"\byour results? (show|indicate|suggest)\b.*\b(disease|disorder|syndrome|condition|anemia|diabetes|hypothyroidism|hyperthyroidism|cancer|deficiency)\b",
]

_DISCLAIMER = (
    "This information is provided for educational purposes only and is not "
    "a medical diagnosis or treatment recommendation — please discuss your results "
    "with your healthcare provider."
)

_DISCLAIMER_BY_LOCALE: dict[str, str] = {
    "en": _DISCLAIMER,
    "uk": (
        "Ця інформація надана виключно в освітніх цілях і не є медичним діагнозом або "
        "рекомендацією щодо лікування — будь ласка, обговоріть свої результати з лікарем."
    ),
}


async def inject_disclaimer(text: str, locale: str = "en") -> str:
    """Append non-diagnostic disclaimer as natural language (final sentence, not footnote)."""
    disclaimer = _DISCLAIMER_BY_LOCALE.get(locale, _DISCLAIMER)
    return f"{text.rstrip()} {disclaimer}"


async def validate_no_diagnostic(text: str) -> str:
    """Raise SafetyValidationError if text contains specific diagnoses or treatment recommendations."""
    for pattern in _FORBIDDEN_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            raise SafetyValidationError(
                f"AI output contains disallowed diagnostic language. Pattern: {pattern}"
            )
    return text


async def surface_uncertainty(text: str, values: Sequence[object] | None = None) -> str:
    """No-op at MVP — uncertainty is surfaced in Claude's prompt rather than post-hoc."""
    return text
