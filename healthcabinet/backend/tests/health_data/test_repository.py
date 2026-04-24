"""Repository tests for encrypted health value persistence."""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.health_data.models import HealthValue
from app.health_data.repository import (
    HealthValueNotFoundError,
    delete_document_health_values,
    flag_health_value,
    list_timeline_values,
    list_values_by_user,
    replace_document_health_values,
    update_document_measured_at,
)
from app.processing.schemas import NormalizedHealthValue


def _normalized_value(
    *,
    biomarker_name: str,
    canonical_biomarker_name: str,
    value: float,
    confidence: float = 0.95,
    needs_review: bool = False,
) -> NormalizedHealthValue:
    return NormalizedHealthValue(
        biomarker_name=biomarker_name,
        canonical_biomarker_name=canonical_biomarker_name,
        value=value,
        unit="mg/dL",
        reference_range_low=70.0,
        reference_range_high=99.0,
        confidence=confidence,
        needs_review=needs_review,
    )


@pytest.mark.asyncio
async def test_replace_document_health_values_encrypts_and_round_trips(
    async_db_session: AsyncSession, make_user, make_document
):
    user, _ = await make_user(email="healthdata-owner@test.com")
    document = await make_document(user=user, status="processing")

    await replace_document_health_values(
        async_db_session,
        document_id=document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            _normalized_value(
                biomarker_name="Glucose", canonical_biomarker_name="glucose", value=91.0
            )
        ],
    )

    stored = (
        await async_db_session.execute(
            select(HealthValue).where(HealthValue.document_id == document.id)
        )
    ).scalar_one()
    assert stored.value_encrypted != b"91.0"

    result = await list_values_by_user(async_db_session, user_id=user.id)
    assert result.skipped_corrupt_records == 0
    assert result.records[0].value == 91.0


@pytest.mark.asyncio
async def test_replace_document_health_values_is_atomic_on_failure(
    async_db_session: AsyncSession, make_user, make_document
):
    user, _ = await make_user(email="healthdata-atomic@test.com")
    document = await make_document(user=user, status="processing")

    with patch(
        "app.health_data.repository.encrypt_bytes",
        side_effect=[b"encrypted-one", RuntimeError("encryption failed")],
    ):
        with pytest.raises(RuntimeError, match="encryption failed"):
            await replace_document_health_values(
                async_db_session,
                document_id=document.id,
                user_id=user.id,
                measured_at=None,
                values=[
                    _normalized_value(
                        biomarker_name="Glucose",
                        canonical_biomarker_name="glucose",
                        value=91.0,
                    ),
                    _normalized_value(
                        biomarker_name="Cholesterol",
                        canonical_biomarker_name="cholesterol_total",
                        value=180.0,
                    ),
                ],
            )
        await async_db_session.rollback()

    stored = (
        (
            await async_db_session.execute(
                select(HealthValue).where(HealthValue.document_id == document.id)
            )
        )
        .scalars()
        .all()
    )
    assert stored == []


@pytest.mark.asyncio
async def test_list_timeline_values_is_user_scoped(
    async_db_session: AsyncSession, make_user, make_document
):
    owner, _ = await make_user(email="timeline-owner@test.com")
    other_user, _ = await make_user(email="timeline-other@test.com")
    owner_document = await make_document(user=owner, status="processing")
    other_document = await make_document(user=other_user, status="processing")

    await replace_document_health_values(
        async_db_session,
        document_id=owner_document.id,
        user_id=owner.id,
        measured_at=None,
        values=[
            _normalized_value(
                biomarker_name="Glucose", canonical_biomarker_name="glucose", value=91.0
            )
        ],
    )
    await replace_document_health_values(
        async_db_session,
        document_id=other_document.id,
        user_id=other_user.id,
        measured_at=None,
        values=[
            _normalized_value(
                biomarker_name="Glucose", canonical_biomarker_name="glucose", value=88.0
            )
        ],
    )

    result = await list_timeline_values(
        async_db_session, user_id=owner.id, canonical_biomarker_name="glucose"
    )

    assert result.skipped_corrupt_records == 0
    assert len(result.records) == 1
    assert result.records[0].user_id == owner.id
    assert result.records[0].value == 91.0


@pytest.mark.asyncio
async def test_list_timeline_values_groups_multiple_documents_by_canonical_name(
    async_db_session: AsyncSession, make_user, make_document
):
    user, _ = await make_user(email="timeline-group@test.com")
    first_document = await make_document(user=user, status="processing")
    second_document = await make_document(user=user, status="processing")

    await replace_document_health_values(
        async_db_session,
        document_id=first_document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            _normalized_value(
                biomarker_name="Glucose", canonical_biomarker_name="glucose", value=91.0
            )
        ],
    )
    await replace_document_health_values(
        async_db_session,
        document_id=second_document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            _normalized_value(
                biomarker_name="Blood Glucose", canonical_biomarker_name="glucose", value=89.0
            )
        ],
    )

    result = await list_timeline_values(
        async_db_session, user_id=user.id, canonical_biomarker_name="glucose"
    )

    assert [record.value for record in result.records] == [91.0, 89.0]


@pytest.mark.asyncio
async def test_replace_document_health_values_rejects_mismatched_user(
    async_db_session: AsyncSession, make_user, make_document
):
    """Document-owner invariant: writing values with a user_id that doesn't match the document owner must fail."""
    owner, _ = await make_user(email="owner-invariant@test.com")
    other_user, _ = await make_user(email="other-invariant@test.com")
    document = await make_document(user=owner, status="processing")

    with pytest.raises(ValueError, match="belongs to user"):
        await replace_document_health_values(
            async_db_session,
            document_id=document.id,
            user_id=other_user.id,
            measured_at=None,
            values=[
                _normalized_value(
                    biomarker_name="Glucose", canonical_biomarker_name="glucose", value=91.0
                )
            ],
        )


@pytest.mark.asyncio
async def test_replace_document_health_values_rejects_nonexistent_document(
    async_db_session: AsyncSession, make_user
):
    """Document-owner invariant: writing values for a nonexistent document must fail."""
    user, _ = await make_user(email="owner-noexist@test.com")

    with pytest.raises(ValueError, match="does not exist"):
        await replace_document_health_values(
            async_db_session,
            document_id=uuid.uuid4(),
            user_id=user.id,
            measured_at=None,
            values=[
                _normalized_value(
                    biomarker_name="Glucose", canonical_biomarker_name="glucose", value=91.0
                )
            ],
        )


@pytest.mark.asyncio
async def test_delete_document_health_values_removes_stale_values(
    async_db_session: AsyncSession, make_user, make_document
):
    """Stale value cleanup: deleting values for a document removes all associated rows."""
    user, _ = await make_user(email="stale-cleanup@test.com")
    document = await make_document(user=user, status="processing")

    await replace_document_health_values(
        async_db_session,
        document_id=document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            _normalized_value(
                biomarker_name="Glucose", canonical_biomarker_name="glucose", value=91.0
            )
        ],
    )

    result_before = await list_values_by_user(async_db_session, user_id=user.id)
    assert len(result_before.records) == 1

    await delete_document_health_values(async_db_session, document_id=document.id)

    result_after = await list_values_by_user(async_db_session, user_id=user.id)
    assert result_after.records == []


@pytest.mark.asyncio
async def test_list_values_by_user_skips_corrupt_rows(
    async_db_session: AsyncSession, make_user, make_document
):
    user, _ = await make_user(email="corrupt-row@test.com")
    document = await make_document(user=user, status="completed")

    await replace_document_health_values(
        async_db_session,
        document_id=document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            _normalized_value(
                biomarker_name="Glucose", canonical_biomarker_name="glucose", value=91.0
            )
        ],
    )
    await async_db_session.execute(
        HealthValue.__table__.update()
        .where(HealthValue.document_id == document.id)
        .values(value_encrypted=b"not-valid-ciphertext")
    )
    await async_db_session.commit()

    result = await list_values_by_user(async_db_session, user_id=user.id)

    assert result.records == []
    assert result.skipped_corrupt_records == 1


@pytest.mark.asyncio
async def test_list_values_by_document_returns_scoped_values(
    async_db_session: AsyncSession, make_user, make_document
):
    """Document-scoped retrieval returns only values for the specified document."""
    from app.health_data.repository import list_values_by_document

    user, _ = await make_user(email="doc-scoped@test.com")
    doc_a = await make_document(user=user, status="completed")
    doc_b = await make_document(user=user, status="completed")

    await replace_document_health_values(
        async_db_session,
        document_id=doc_a.id,
        user_id=user.id,
        measured_at=None,
        values=[
            _normalized_value(
                biomarker_name="Glucose", canonical_biomarker_name="glucose", value=91.0
            )
        ],
    )
    await replace_document_health_values(
        async_db_session,
        document_id=doc_b.id,
        user_id=user.id,
        measured_at=None,
        values=[
            _normalized_value(
                biomarker_name="Cholesterol",
                canonical_biomarker_name="cholesterol_total",
                value=180.0,
            )
        ],
    )

    result = await list_values_by_document(async_db_session, document_id=doc_a.id, user_id=user.id)
    assert len(result.records) == 1
    assert result.records[0].canonical_biomarker_name == "glucose"
    assert result.skipped_corrupt_records == 0


@pytest.mark.asyncio
async def test_list_values_by_document_user_isolation(
    async_db_session: AsyncSession, make_user, make_document
):
    """Document-scoped retrieval enforces user ownership — other user gets no results."""
    from app.health_data.repository import list_values_by_document

    owner, _ = await make_user(email="doc-scope-owner@test.com")
    other, _ = await make_user(email="doc-scope-other@test.com")
    doc = await make_document(user=owner, status="completed")

    await replace_document_health_values(
        async_db_session,
        document_id=doc.id,
        user_id=owner.id,
        measured_at=None,
        values=[
            _normalized_value(
                biomarker_name="Glucose", canonical_biomarker_name="glucose", value=91.0
            )
        ],
    )

    result = await list_values_by_document(async_db_session, document_id=doc.id, user_id=other.id)
    assert result.records == []


# ────────────────────────────────────────────────────────────────────────────────
# Story 2.6 — value flagging
# ────────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_flag_health_value_sets_is_flagged_and_flagged_at(
    async_db_session: AsyncSession, make_user, make_document
):
    """First flag sets is_flagged=True and records a stable flagged_at timestamp."""
    user, _ = await make_user(email="flag-first@test.com")
    document = await make_document(user=user, status="completed")

    rows = await replace_document_health_values(
        async_db_session,
        document_id=document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            _normalized_value(
                biomarker_name="Glucose", canonical_biomarker_name="glucose", value=91.0
            )
        ],
    )
    health_value_id = rows[0].id

    record = await flag_health_value(
        async_db_session, health_value_id=health_value_id, user_id=user.id
    )

    assert record.is_flagged is True
    assert record.flagged_at is not None


@pytest.mark.asyncio
async def test_flag_health_value_idempotent_preserves_flagged_at(
    async_db_session: AsyncSession, make_user, make_document
):
    """Repeated flag calls do not corrupt flagged_at — the original timestamp is preserved."""
    user, _ = await make_user(email="flag-idempotent@test.com")
    document = await make_document(user=user, status="completed")

    rows = await replace_document_health_values(
        async_db_session,
        document_id=document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            _normalized_value(
                biomarker_name="Glucose", canonical_biomarker_name="glucose", value=91.0
            )
        ],
    )
    health_value_id = rows[0].id

    first = await flag_health_value(
        async_db_session, health_value_id=health_value_id, user_id=user.id
    )
    second = await flag_health_value(
        async_db_session, health_value_id=health_value_id, user_id=user.id
    )

    assert second.is_flagged is True
    assert second.flagged_at == first.flagged_at


@pytest.mark.asyncio
async def test_flag_health_value_owner_only(
    async_db_session: AsyncSession, make_user, make_document
):
    """Flagging a value owned by another user raises HealthValueNotFoundError."""
    owner, _ = await make_user(email="flag-owner@test.com")
    other, _ = await make_user(email="flag-other@test.com")
    document = await make_document(user=owner, status="completed")

    rows = await replace_document_health_values(
        async_db_session,
        document_id=document.id,
        user_id=owner.id,
        measured_at=None,
        values=[
            _normalized_value(
                biomarker_name="Glucose", canonical_biomarker_name="glucose", value=91.0
            )
        ],
    )
    health_value_id = rows[0].id

    with pytest.raises(HealthValueNotFoundError):
        await flag_health_value(async_db_session, health_value_id=health_value_id, user_id=other.id)


@pytest.mark.asyncio
async def test_flag_health_value_unknown_id(async_db_session: AsyncSession, make_user):
    """Flagging a nonexistent health value raises HealthValueNotFoundError."""
    user, _ = await make_user(email="flag-unknown@test.com")

    with pytest.raises(HealthValueNotFoundError):
        await flag_health_value(async_db_session, health_value_id=uuid.uuid4(), user_id=user.id)


@pytest.mark.asyncio
async def test_flag_health_value_does_not_alter_encrypted_value_or_confidence(
    async_db_session: AsyncSession, make_user, make_document
):
    """Flagging must not mutate value_encrypted, confidence, needs_review, or document_id."""
    user, _ = await make_user(email="flag-integrity@test.com")
    document = await make_document(user=user, status="completed")

    rows = await replace_document_health_values(
        async_db_session,
        document_id=document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            _normalized_value(
                biomarker_name="Glucose",
                canonical_biomarker_name="glucose",
                value=91.0,
                confidence=0.95,
                needs_review=False,
            )
        ],
    )
    health_value_id = rows[0].id
    before = rows[0].value_encrypted

    record = await flag_health_value(
        async_db_session, health_value_id=health_value_id, user_id=user.id
    )

    stored = (
        await async_db_session.execute(select(HealthValue).where(HealthValue.id == health_value_id))
    ).scalar_one()

    assert stored.value_encrypted == before
    assert record.confidence == 0.95
    assert record.needs_review is False
    assert record.document_id == document.id


@pytest.mark.asyncio
async def test_flag_health_value_uses_row_lock_for_first_flag_transition():
    """Flagging must lock the row so concurrent requests cannot both assign flagged_at."""

    class _ScalarResult:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    row = SimpleNamespace(is_flagged=False, flagged_at=None)
    captured_statement = None

    async def _execute(statement):
        nonlocal captured_statement
        captured_statement = statement
        return _ScalarResult(row)

    db = AsyncMock(spec=AsyncSession)
    db.execute.side_effect = _execute
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    expected = object()
    with patch("app.health_data.repository._to_record", return_value=expected):
        result = await flag_health_value(
            db,
            health_value_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )

    assert result is expected
    assert captured_statement is not None
    compiled_sql = str(
        captured_statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "FOR UPDATE" in compiled_sql
    db.flush.assert_awaited_once()
    db.refresh.assert_awaited_once_with(row)


# ────────────────────────────────────────────────────────────────────────────────
# Story 15.2 — bulk measured_at update for year confirmation
# ────────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_document_measured_at_is_user_scoped(
    async_db_session: AsyncSession, make_user, make_document
):
    """User-scoped bulk update must ONLY touch rows for (document_id, user_id).

    Two users, one document each. Updating user A's document must leave user
    B's rows untouched. The return value must match the number of rows touched.
    """
    user_a, _ = await make_user(email="measured-at-a@test.com")
    user_b, _ = await make_user(email="measured-at-b@test.com")
    doc_a = await make_document(user=user_a, status="partial")
    doc_b = await make_document(user=user_b, status="partial")

    await replace_document_health_values(
        async_db_session,
        document_id=doc_a.id,
        user_id=user_a.id,
        measured_at=None,
        values=[
            _normalized_value(
                biomarker_name="Glucose", canonical_biomarker_name="glucose", value=91.0
            ),
            _normalized_value(
                biomarker_name="Cholesterol",
                canonical_biomarker_name="cholesterol_total",
                value=180.0,
            ),
        ],
    )
    await replace_document_health_values(
        async_db_session,
        document_id=doc_b.id,
        user_id=user_b.id,
        measured_at=None,
        values=[
            _normalized_value(
                biomarker_name="Glucose", canonical_biomarker_name="glucose", value=88.0
            ),
        ],
    )

    resolved_at = datetime(2026, 3, 12, 0, 0, 0, tzinfo=UTC)
    rowcount = await update_document_measured_at(
        async_db_session,
        document_id=doc_a.id,
        user_id=user_a.id,
        measured_at=resolved_at,
    )
    await async_db_session.commit()

    # Return value = rows touched.
    assert rowcount == 2

    # User A's rows carry the resolved timestamp.
    rows_a = (
        (
            await async_db_session.execute(
                select(HealthValue).where(HealthValue.document_id == doc_a.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows_a) == 2
    for row in rows_a:
        assert row.measured_at is not None
        actual = row.measured_at if row.measured_at.tzinfo else row.measured_at.replace(tzinfo=UTC)
        assert actual == resolved_at

    # User B's row is untouched — measured_at still null.
    rows_b = (
        (
            await async_db_session.execute(
                select(HealthValue).where(HealthValue.document_id == doc_b.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows_b) == 1
    assert rows_b[0].measured_at is None


@pytest.mark.asyncio
async def test_update_document_measured_at_mismatched_user_updates_zero_rows(
    async_db_session: AsyncSession, make_user, make_document
):
    """Calling with a user_id that doesn't own the document updates 0 rows (defense-in-depth)."""
    owner, _ = await make_user(email="measured-at-owner@test.com")
    attacker, _ = await make_user(email="measured-at-attacker@test.com")
    doc = await make_document(user=owner, status="partial")

    await replace_document_health_values(
        async_db_session,
        document_id=doc.id,
        user_id=owner.id,
        measured_at=None,
        values=[
            _normalized_value(
                biomarker_name="Glucose", canonical_biomarker_name="glucose", value=91.0
            )
        ],
    )

    resolved_at = datetime(2026, 3, 12, tzinfo=UTC)
    rowcount = await update_document_measured_at(
        async_db_session,
        document_id=doc.id,
        user_id=attacker.id,  # wrong owner
        measured_at=resolved_at,
    )
    assert rowcount == 0

    rows = (
        (
            await async_db_session.execute(
                select(HealthValue).where(HealthValue.document_id == doc.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].measured_at is None
