"""HTTP tests for health value retrieval routes."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.processing.schemas import NormalizedHealthValue


def _auth_headers(user_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


@pytest_asyncio.fixture
async def health_client(async_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield async_db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_health_values_returns_user_rows(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user, make_document
):
    from app.health_data.repository import replace_document_health_values

    user, _ = await make_user(email="health-route@test.com")
    document = await make_document(user=user, status="completed")

    await replace_document_health_values(
        async_db_session,
        document_id=document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            NormalizedHealthValue(
                biomarker_name="Glucose",
                canonical_biomarker_name="glucose",
                value=91.0,
                unit="mg/dL",
                reference_range_low=70.0,
                reference_range_high=99.0,
                confidence=0.95,
                needs_review=False,
            )
        ],
    )

    response = await health_client.get("/api/v1/health-values", headers=_auth_headers(user.id))

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["canonical_biomarker_name"] == "glucose"
    assert data[0]["value"] == 91.0


@pytest.mark.asyncio
async def test_get_health_value_timeline_returns_canonical_series(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user, make_document
):
    from app.health_data.repository import replace_document_health_values

    user, _ = await make_user(email="health-timeline@test.com")
    first_document = await make_document(user=user, status="completed")
    second_document = await make_document(user=user, status="completed")

    await replace_document_health_values(
        async_db_session,
        document_id=first_document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            NormalizedHealthValue(
                biomarker_name="Glucose",
                canonical_biomarker_name="glucose",
                value=91.0,
                unit="mg/dL",
                reference_range_low=70.0,
                reference_range_high=99.0,
                confidence=0.95,
                needs_review=False,
            )
        ],
    )
    await replace_document_health_values(
        async_db_session,
        document_id=second_document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            NormalizedHealthValue(
                biomarker_name="Blood Glucose",
                canonical_biomarker_name="glucose",
                value=89.0,
                unit="mg/dL",
                reference_range_low=70.0,
                reference_range_high=99.0,
                confidence=0.9,
                needs_review=False,
            )
        ],
    )

    response = await health_client.get(
        "/api/v1/health-values/timeline/glucose",
        headers=_auth_headers(user.id),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["biomarker_name"] == "glucose"
    assert data["canonical_biomarker_name"] == "glucose"
    assert [value["value"] for value in data["values"]] == [91.0, 89.0]


@pytest.mark.asyncio
async def test_get_health_value_timeline_normalizes_input_name(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user, make_document
):
    from app.health_data.repository import replace_document_health_values

    user, _ = await make_user(email="health-timeline-normalized@test.com")
    document = await make_document(user=user, status="completed")

    await replace_document_health_values(
        async_db_session,
        document_id=document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            NormalizedHealthValue(
                biomarker_name="Glucose",
                canonical_biomarker_name="glucose",
                value=91.0,
                unit="mg/dL",
                reference_range_low=70.0,
                reference_range_high=99.0,
                confidence=0.95,
                needs_review=False,
            )
        ],
    )

    response = await health_client.get(
        "/api/v1/health-values/timeline/Blood%20Glucose",
        headers=_auth_headers(user.id),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["biomarker_name"] == "Blood Glucose"
    assert data["canonical_biomarker_name"] == "glucose"
    assert [value["value"] for value in data["values"]] == [91.0]


# ────────────────────────────────────────────────────────────────────────────────
# Story 2.6 — flag endpoint
# ────────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_flag_health_value_returns_flagged_response(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user, make_document
):
    """PUT /api/v1/health-values/{id}/flag returns is_flagged=True with a timestamp."""
    from app.health_data.repository import replace_document_health_values

    user, _ = await make_user(email="flag-route@test.com")
    document = await make_document(user=user, status="completed")

    rows = await replace_document_health_values(
        async_db_session,
        document_id=document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            NormalizedHealthValue(
                biomarker_name="Glucose",
                canonical_biomarker_name="glucose",
                value=91.0,
                unit="mg/dL",
                reference_range_low=70.0,
                reference_range_high=99.0,
                confidence=0.95,
                needs_review=False,
            )
        ],
    )

    response = await health_client.put(
        f"/api/v1/health-values/{rows[0].id}/flag",
        headers=_auth_headers(user.id),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(rows[0].id)
    assert data["is_flagged"] is True
    assert data["flagged_at"] is not None


@pytest.mark.asyncio
async def test_flag_health_value_returns_404_for_unknown_id(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user
):
    """PUT flag on a nonexistent health value returns RFC 7807 404."""
    import uuid

    user, _ = await make_user(email="flag-404@test.com")

    response = await health_client.put(
        f"/api/v1/health-values/{uuid.uuid4()}/flag",
        headers=_auth_headers(user.id),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_flag_health_value_returns_404_for_other_users_value(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user, make_document
):
    """Attempting to flag another user's value returns 404 (no ownership leakage)."""
    from app.health_data.repository import replace_document_health_values

    owner, _ = await make_user(email="flag-own@test.com")
    attacker, _ = await make_user(email="flag-attacker@test.com")
    document = await make_document(user=owner, status="completed")

    rows = await replace_document_health_values(
        async_db_session,
        document_id=document.id,
        user_id=owner.id,
        measured_at=None,
        values=[
            NormalizedHealthValue(
                biomarker_name="Glucose",
                canonical_biomarker_name="glucose",
                value=91.0,
                unit="mg/dL",
                reference_range_low=70.0,
                reference_range_high=99.0,
                confidence=0.95,
                needs_review=False,
            )
        ],
    )

    response = await health_client.put(
        f"/api/v1/health-values/{rows[0].id}/flag",
        headers=_auth_headers(attacker.id),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_flag_health_value_unauthenticated_returns_401(
    health_client: AsyncClient,
):
    """Unauthenticated flag request returns 401."""
    import uuid

    response = await health_client.put(f"/api/v1/health-values/{uuid.uuid4()}/flag")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_flag_health_value_response_includes_is_flagged_and_flagged_at_in_list(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user, make_document
):
    """After flagging, GET /health-values returns the value with is_flagged=True."""
    from app.health_data.repository import replace_document_health_values

    user, _ = await make_user(email="flag-list-check@test.com")
    document = await make_document(user=user, status="completed")

    rows = await replace_document_health_values(
        async_db_session,
        document_id=document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            NormalizedHealthValue(
                biomarker_name="Glucose",
                canonical_biomarker_name="glucose",
                value=91.0,
                unit="mg/dL",
                reference_range_low=70.0,
                reference_range_high=99.0,
                confidence=0.95,
                needs_review=False,
            )
        ],
    )

    await health_client.put(
        f"/api/v1/health-values/{rows[0].id}/flag",
        headers=_auth_headers(user.id),
    )

    list_response = await health_client.get(
        "/api/v1/health-values", headers=_auth_headers(user.id)
    )

    assert list_response.status_code == 200
    values = list_response.json()
    assert values[0]["is_flagged"] is True
    assert values[0]["flagged_at"] is not None


# ────────────────────────────────────────────────────────────────────────────────
# Story 3.1 — baseline endpoint
# ────────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_baseline_unauthenticated_returns_401(health_client: AsyncClient):
    """GET /health-values/baseline without auth returns 401."""
    response = await health_client.get("/api/v1/health-values/baseline")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_baseline_no_profile_returns_general_recommendations(
    health_client: AsyncClient, make_user
):
    """User with no profile row gets general recommendations within the 3–5 bounds."""
    user, _ = await make_user(email="baseline-no-profile@test.com")

    response = await health_client.get(
        "/api/v1/health-values/baseline",
        headers=_auth_headers(user.id),
    )

    assert response.status_code == 200
    data = response.json()
    assert 3 <= len(data["recommendations"]) <= 5
    assert all(r["category"] == "general" for r in data["recommendations"])
    assert data["has_uploads"] is False


@pytest.mark.asyncio
async def test_baseline_no_conditions_returns_general_recommendations(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user
):
    """User with a profile but no known_conditions gets only general recommendations."""
    from app.users.repository import upsert_user_profile

    user, _ = await make_user(email="baseline-no-conditions@test.com")
    await upsert_user_profile(
        async_db_session,
        user.id,
        age=30,
        sex="male",
        known_conditions=[],
    )

    response = await health_client.get(
        "/api/v1/health-values/baseline",
        headers=_auth_headers(user.id),
    )

    assert response.status_code == 200
    data = response.json()
    assert 3 <= len(data["recommendations"]) <= 5
    assert all(r["category"] == "general" for r in data["recommendations"])


@pytest.mark.asyncio
async def test_baseline_with_hashimotos_includes_thyroid_recommendation(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user
):
    """User with Hashimoto's gets a condition-specific thyroid panel recommendation."""
    from app.users.repository import upsert_user_profile

    user, _ = await make_user(email="baseline-hashimotos@test.com")
    await upsert_user_profile(
        async_db_session,
        user.id,
        age=35,
        sex="female",
        known_conditions=["Hashimoto's disease"],
    )

    response = await health_client.get(
        "/api/v1/health-values/baseline",
        headers=_auth_headers(user.id),
    )

    assert response.status_code == 200
    data = response.json()
    recs = data["recommendations"]
    thyroid_recs = [r for r in recs if "TSH" in r["test_name"]]
    assert len(thyroid_recs) == 1
    assert thyroid_recs[0]["category"] == "condition_specific"
    assert thyroid_recs[0]["frequency"] == "Every 6 months"


@pytest.mark.asyncio
async def test_baseline_with_diabetes_includes_hba1c_recommendation(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user
):
    """User with Type 2 Diabetes gets a condition-specific HbA1c recommendation."""
    from app.users.repository import upsert_user_profile

    user, _ = await make_user(email="baseline-diabetes@test.com")
    await upsert_user_profile(
        async_db_session,
        user.id,
        age=45,
        sex="male",
        known_conditions=["Type 2 Diabetes"],
    )

    response = await health_client.get(
        "/api/v1/health-values/baseline",
        headers=_auth_headers(user.id),
    )

    assert response.status_code == 200
    data = response.json()
    recs = data["recommendations"]
    hba1c_recs = [r for r in recs if "HbA1c" in r["test_name"]]
    assert len(hba1c_recs) == 1
    assert hba1c_recs[0]["category"] == "condition_specific"


@pytest.mark.asyncio
async def test_baseline_recommendation_count_within_bounds(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user
):
    """Even with many conditions the count stays within 3–5."""
    from app.users.repository import upsert_user_profile

    user, _ = await make_user(email="baseline-many-conditions@test.com")
    await upsert_user_profile(
        async_db_session,
        user.id,
        age=50,
        sex="female",
        known_conditions=[
            "Hashimoto's disease",
            "Type 2 Diabetes",
            "Hypertension",
            "High cholesterol",
            "Anemia",
            "PCOS",
        ],
    )

    response = await health_client.get(
        "/api/v1/health-values/baseline",
        headers=_auth_headers(user.id),
    )

    assert response.status_code == 200
    data = response.json()
    assert 3 <= len(data["recommendations"]) <= 5


@pytest.mark.asyncio
async def test_baseline_has_uploads_is_false_when_no_documents(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user
):
    """has_uploads is False when the user has no document rows."""
    from app.users.repository import upsert_user_profile

    user, _ = await make_user(email="baseline-uploads-false@test.com")
    await upsert_user_profile(async_db_session, user.id, age=28, sex="female", known_conditions=[])

    response = await health_client.get(
        "/api/v1/health-values/baseline",
        headers=_auth_headers(user.id),
    )

    assert response.status_code == 200
    assert response.json()["has_uploads"] is False


@pytest.mark.asyncio
async def test_baseline_has_uploads_is_true_when_documents_exist(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user, make_document
):
    """has_uploads is True when the user has at least one document row."""
    user, _ = await make_user(email="baseline-uploads-true@test.com")
    await make_document(user=user)

    response = await health_client.get(
        "/api/v1/health-values/baseline",
        headers=_auth_headers(user.id),
    )

    assert response.status_code == 200
    assert response.json()["has_uploads"] is True


# ────────────────────────────────────────────────────────────────────────────────
# Story 3.2 — status field and context indicators
# ────────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_health_values_includes_status_field(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user, make_document
):
    """GET /health-values returns a status field on each value."""
    from app.health_data.repository import replace_document_health_values

    user, _ = await make_user(email="status-field@test.com")
    document = await make_document(user=user, status="completed")

    await replace_document_health_values(
        async_db_session,
        document_id=document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            NormalizedHealthValue(
                biomarker_name="Glucose",
                canonical_biomarker_name="glucose",
                value=91.0,
                unit="mg/dL",
                reference_range_low=70.0,
                reference_range_high=99.0,
                confidence=0.95,
                needs_review=False,
            )
        ],
    )

    response = await health_client.get("/api/v1/health-values", headers=_auth_headers(user.id))

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "status" in data[0]
    assert data[0]["status"] == "optimal"


@pytest.mark.asyncio
async def test_get_health_values_status_optimal_for_in_range_value(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user, make_document
):
    """Value within reference range is classified as optimal."""
    from app.health_data.repository import replace_document_health_values

    user, _ = await make_user(email="status-optimal@test.com")
    document = await make_document(user=user, status="completed")

    await replace_document_health_values(
        async_db_session,
        document_id=document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            NormalizedHealthValue(
                biomarker_name="Glucose",
                canonical_biomarker_name="glucose",
                value=91.0,
                unit="mg/dL",
                reference_range_low=70.0,
                reference_range_high=99.0,
                confidence=0.95,
                needs_review=False,
            )
        ],
    )

    response = await health_client.get("/api/v1/health-values", headers=_auth_headers(user.id))

    assert response.status_code == 200
    assert response.json()[0]["status"] == "optimal"


@pytest.mark.asyncio
async def test_get_health_values_status_borderline_for_slightly_out_of_range(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user, make_document
):
    """Value slightly outside reference range is classified as borderline.

    ref_low=70, ref_high=99, value=65: span=29, pct=(70-65)/29≈0.17 ≤ 0.20 → borderline
    """
    from app.health_data.repository import replace_document_health_values

    user, _ = await make_user(email="status-borderline@test.com")
    document = await make_document(user=user, status="completed")

    await replace_document_health_values(
        async_db_session,
        document_id=document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            NormalizedHealthValue(
                biomarker_name="Glucose",
                canonical_biomarker_name="glucose",
                value=65.0,
                unit="mg/dL",
                reference_range_low=70.0,
                reference_range_high=99.0,
                confidence=0.95,
                needs_review=False,
            )
        ],
    )

    response = await health_client.get("/api/v1/health-values", headers=_auth_headers(user.id))

    assert response.status_code == 200
    assert response.json()[0]["status"] == "borderline"


@pytest.mark.asyncio
async def test_get_health_values_status_action_needed_for_far_out_of_range(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user, make_document
):
    """Value far outside reference range is classified as action_needed.

    ref_low=70, ref_high=99, value=30: span=29, pct=(70-30)/29≈1.38 > 0.50 → action_needed
    """
    from app.health_data.repository import replace_document_health_values

    user, _ = await make_user(email="status-action-needed@test.com")
    document = await make_document(user=user, status="completed")

    await replace_document_health_values(
        async_db_session,
        document_id=document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            NormalizedHealthValue(
                biomarker_name="Glucose",
                canonical_biomarker_name="glucose",
                value=30.0,
                unit="mg/dL",
                reference_range_low=70.0,
                reference_range_high=99.0,
                confidence=0.95,
                needs_review=False,
            )
        ],
    )

    response = await health_client.get("/api/v1/health-values", headers=_auth_headers(user.id))

    assert response.status_code == 200
    assert response.json()[0]["status"] == "action_needed"


@pytest.mark.asyncio
async def test_get_health_values_status_unknown_when_no_reference_range(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user, make_document
):
    """Value with no reference range bounds is classified as unknown."""
    from app.health_data.repository import replace_document_health_values

    user, _ = await make_user(email="status-unknown@test.com")
    document = await make_document(user=user, status="completed")

    await replace_document_health_values(
        async_db_session,
        document_id=document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            NormalizedHealthValue(
                biomarker_name="SomeMarker",
                canonical_biomarker_name="some_marker",
                value=42.0,
                unit=None,
                reference_range_low=None,
                reference_range_high=None,
                confidence=0.85,
                needs_review=False,
            )
        ],
    )

    response = await health_client.get("/api/v1/health-values", headers=_auth_headers(user.id))

    assert response.status_code == 200
    assert response.json()[0]["status"] == "unknown"


@pytest.mark.asyncio
async def test_get_health_values_status_concerning_for_moderately_out_of_range(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user, make_document
):
    """Value moderately outside reference range is classified as concerning.

    ref_low=70, ref_high=99, value=58: span=29, pct=(70-58)/29≈0.41 → 0.20 < pct ≤ 0.50 → concerning
    """
    from app.health_data.repository import replace_document_health_values

    user, _ = await make_user(email="status-concerning@test.com")
    document = await make_document(user=user, status="completed")

    await replace_document_health_values(
        async_db_session,
        document_id=document.id,
        user_id=user.id,
        measured_at=None,
        values=[
            NormalizedHealthValue(
                biomarker_name="Glucose",
                canonical_biomarker_name="glucose",
                value=58.0,
                unit="mg/dL",
                reference_range_low=70.0,
                reference_range_high=99.0,
                confidence=0.95,
                needs_review=False,
            )
        ],
    )

    response = await health_client.get("/api/v1/health-values", headers=_auth_headers(user.id))

    assert response.status_code == 200
    assert response.json()[0]["status"] == "concerning"


# ────────────────────────────────────────────────────────────────────────────────
# Story 3.3 — timeline ordering and empty-biomarker edge case
# ────────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_health_value_timeline_returns_ordered_values(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user, make_document
):
    """Timeline returns values oldest-first for a given canonical biomarker."""
    from datetime import datetime, timezone

    from app.health_data.repository import replace_document_health_values

    user, _ = await make_user(email="timeline-order@test.com")
    doc1 = await make_document(user=user, status="completed")
    doc2 = await make_document(user=user, status="completed")

    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2026, 3, 1, tzinfo=timezone.utc)

    await replace_document_health_values(
        async_db_session,
        document_id=doc1.id,
        user_id=user.id,
        measured_at=t1,
        values=[
            NormalizedHealthValue(
                biomarker_name="Glucose",
                canonical_biomarker_name="glucose",
                value=91.0,
                unit="mg/dL",
                reference_range_low=70.0,
                reference_range_high=99.0,
                confidence=0.95,
                needs_review=False,
            )
        ],
    )
    await replace_document_health_values(
        async_db_session,
        document_id=doc2.id,
        user_id=user.id,
        measured_at=t2,
        values=[
            NormalizedHealthValue(
                biomarker_name="Glucose",
                canonical_biomarker_name="glucose",
                value=86.0,
                unit="mg/dL",
                reference_range_low=70.0,
                reference_range_high=99.0,
                confidence=0.92,
                needs_review=False,
            )
        ],
    )

    response = await health_client.get(
        "/api/v1/health-values/timeline/glucose",
        headers=_auth_headers(user.id),
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["values"]) == 2
    # Oldest-first ordering
    assert data["values"][0]["measured_at"] < data["values"][1]["measured_at"]
    assert data["values"][0]["value"] == 91.0
    assert data["values"][1]["value"] == 86.0
    assert data["canonical_biomarker_name"] == "glucose"


@pytest.mark.asyncio
async def test_get_health_value_timeline_empty_returns_empty_list(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user
):
    """Timeline for a biomarker with no values returns empty list and 0 skipped records."""
    user, _ = await make_user(email="timeline-empty@test.com")

    response = await health_client.get(
        "/api/v1/health-values/timeline/nonexistent_biomarker_xyz",
        headers=_auth_headers(user.id),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["values"] == []
    assert data["skipped_corrupt_records"] == 0


# ---------------------------------------------------------------------------
# Story 15.3 — document_kind filter on GET /health-values
# ---------------------------------------------------------------------------


async def _seed_kind_dataset(
    db: AsyncSession, make_user, make_document
):
    """Seed one user with 3 documents (analysis/document/unknown) each with 1 value."""
    from app.health_data.repository import replace_document_health_values

    user, _ = await make_user(email="kind-filter@test.com")

    def _make_value(name: str, val: float) -> NormalizedHealthValue:
        return NormalizedHealthValue(
            biomarker_name=name,
            canonical_biomarker_name=name.lower(),
            value=val,
            unit="mg/dL",
            reference_range_low=0.0,
            reference_range_high=100.0,
            confidence=0.95,
            needs_review=False,
        )

    analysis_doc = await make_document(user=user, status="completed")
    analysis_doc.document_kind = "analysis"
    document_doc = await make_document(user=user, status="completed")
    document_doc.document_kind = "document"
    unknown_doc = await make_document(user=user, status="failed")
    unknown_doc.document_kind = "unknown"
    await db.flush()

    await replace_document_health_values(
        db,
        document_id=analysis_doc.id,
        user_id=user.id,
        measured_at=None,
        values=[_make_value("Glucose", 90.0)],
    )
    await replace_document_health_values(
        db,
        document_id=document_doc.id,
        user_id=user.id,
        measured_at=None,
        values=[_make_value("Cholesterol", 180.0)],
    )
    await replace_document_health_values(
        db,
        document_id=unknown_doc.id,
        user_id=user.id,
        measured_at=None,
        values=[_make_value("Triglycerides", 120.0)],
    )

    return user, analysis_doc, document_doc, unknown_doc


@pytest.mark.asyncio
async def test_get_health_values_no_filter_returns_all_kinds_including_unknown(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user, make_document
):
    """Back-compat: no filter returns every value, including unknown-owner rows."""
    user, *_ = await _seed_kind_dataset(async_db_session, make_user, make_document)

    response = await health_client.get(
        "/api/v1/health-values",
        headers=_auth_headers(user.id),
    )

    assert response.status_code == 200
    data = response.json()
    names = sorted(v["canonical_biomarker_name"] for v in data)
    assert names == ["cholesterol", "glucose", "triglycerides"]


@pytest.mark.asyncio
async def test_get_health_values_filter_all_excludes_unknown(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user, make_document
):
    user, *_ = await _seed_kind_dataset(async_db_session, make_user, make_document)

    response = await health_client.get(
        "/api/v1/health-values?document_kind=all",
        headers=_auth_headers(user.id),
    )

    assert response.status_code == 200
    names = sorted(v["canonical_biomarker_name"] for v in response.json())
    assert names == ["cholesterol", "glucose"]


@pytest.mark.asyncio
async def test_get_health_values_filter_analysis_only(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user, make_document
):
    user, *_ = await _seed_kind_dataset(async_db_session, make_user, make_document)

    response = await health_client.get(
        "/api/v1/health-values?document_kind=analysis",
        headers=_auth_headers(user.id),
    )

    assert response.status_code == 200
    names = sorted(v["canonical_biomarker_name"] for v in response.json())
    assert names == ["glucose"]


@pytest.mark.asyncio
async def test_get_health_values_filter_document_only(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user, make_document
):
    user, *_ = await _seed_kind_dataset(async_db_session, make_user, make_document)

    response = await health_client.get(
        "/api/v1/health-values?document_kind=document",
        headers=_auth_headers(user.id),
    )

    assert response.status_code == 200
    names = sorted(v["canonical_biomarker_name"] for v in response.json())
    assert names == ["cholesterol"]


@pytest.mark.asyncio
async def test_get_health_values_filter_unknown_rejected(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user
):
    """Literal excludes 'unknown' — Pydantic returns 422."""
    user, _ = await make_user(email="kind-unknown-reject@test.com")

    response = await health_client.get(
        "/api/v1/health-values?document_kind=unknown",
        headers=_auth_headers(user.id),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_health_values_filter_ownership_scoped(
    health_client: AsyncClient, async_db_session: AsyncSession, make_user, make_document
):
    """User B's analysis value must never appear in user A's analysis filter."""
    from app.health_data.repository import replace_document_health_values

    user_a, *_ = await _seed_kind_dataset(async_db_session, make_user, make_document)
    user_b, _ = await make_user(email="kind-filter-other@test.com")
    doc_b = await make_document(user=user_b, status="completed")
    doc_b.document_kind = "analysis"
    await async_db_session.flush()

    await replace_document_health_values(
        async_db_session,
        document_id=doc_b.id,
        user_id=user_b.id,
        measured_at=None,
        values=[
            NormalizedHealthValue(
                biomarker_name="HbA1c",
                canonical_biomarker_name="hba1c",
                value=5.4,
                unit="%",
                reference_range_low=4.0,
                reference_range_high=5.7,
                confidence=0.9,
                needs_review=False,
            )
        ],
    )

    response = await health_client.get(
        "/api/v1/health-values?document_kind=analysis",
        headers=_auth_headers(user_a.id),
    )

    assert response.status_code == 200
    names = {v["canonical_biomarker_name"] for v in response.json()}
    assert "hba1c" not in names
    assert names == {"glucose"}
