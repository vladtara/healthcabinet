"""Unit tests for `_parse_partial_date` — Story 15.2 AC 3.

These tests intentionally exercise the private parser directly. The shapes here
mirror the emissions the extractor produces for yearless dates; full dates with
an embedded year must fall through to None because the year is supplied by the
user via the confirmation flow, not recovered from the fragment.
"""

import pytest

from app.documents.service import _parse_partial_date


@pytest.mark.parametrize(
    ("fragment", "expected"),
    [
        # Numeric dd/mm shapes — the first pattern in _PARTIAL_DATE_PATTERNS.
        ("12.03", (12, 3)),
        ("12/03", (12, 3)),
        ("12-03", (12, 3)),
        # Day + named month, whitespace separator (pre-existing support).
        ("12 Mar", (12, 3)),
        ("12 March", (12, 3)),
        # Day + named month, hyphen separator (new with Fix J).
        ("12-Mar", (12, 3)),
        # Named month + day, whitespace (pre-existing).
        ("Mar 12", (12, 3)),
        # Named month + day, hyphen (new with Fix J).
        ("Mar-12", (12, 3)),
        # Accepted abbreviations.
        ("Sept 5", (5, 9)),
        # Negative cases — must return None, never fabricate a date.
        ("", None),
        ("garbage", None),
        # Full dates (with year) must not round-trip through the parser — the
        # year is supplied by the user; treating "12.03.2024" as a partial
        # would let clients double-write the year.
        ("12.03.2024", None),
    ],
)
def test_parse_partial_date_matrix(fragment: str, expected: tuple[int, int] | None) -> None:
    assert _parse_partial_date(fragment) == expected
