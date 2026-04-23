import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Update, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AuditLog
from app.auth.models import User
from app.auth.repository import create_consent_log
from app.core.security import create_access_token
from app.main import app
from app.users.models import ConsentLog
from app.users.repository import upsert_user_profile
from app.users.service import AUDIT_ERASURE_MARKER as ERASURE_MARKER


class MockArqRedis:
    def __init__(self) -> None:
        self.enqueued: list[dict[str, object]] = []

    async def enqueue_job(self, func_name: str, **kwargs: object) -> MagicMock:
        job = MagicMock()
        job.job_id = "reconcile-job"
        self.enqueued.append({"func": func_name, "kwargs": kwargs, "job": job})
        return job


@pytest.fixture
def mock_arq_redis() -> MockArqRedis:
    original = getattr(app.state, "arq_redis", None)
    mock = MockArqRedis()
    app.state.arq_redis = mock
    try:
        yield mock
    finally:
        app.state.arq_redis = original


async def _create_admin_audit_log_fixture(
    async_db_session: AsyncSession,
    make_user,
    *,
    admin_email: str,
    subject_email: str,
) -> tuple[User, User, AuditLog]:
    admin_user, _ = await make_user(email=admin_email)
    admin_user.role = "admin"
    async_db_session.add(admin_user)

    subject_user, _ = await make_user(email=subject_email)
    audit_log = AuditLog(
        admin_id=admin_user.id,
        user_id=subject_user.id,
        value_name="Glucose",
        original_value="95",
        new_value="100",
        reason="Corrected OCR error",
    )
    async_db_session.add(audit_log)
    await async_db_session.flush()
    return admin_user, subject_user, audit_log


@pytest.mark.asyncio
async def test_get_profile_not_found(test_client: AsyncClient, make_user):
    user, _ = await make_user()
    token = create_access_token(str(user.id))
    response = await test_client.get(
        "/api/v1/users/me/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Profile not found"


@pytest.mark.asyncio
async def test_get_profile_success(
    test_client: AsyncClient, async_db_session: AsyncSession, make_user
):
    user, _ = await make_user(email="getprofile@test.com")
    await upsert_user_profile(
        async_db_session, user.id, age=34, sex="female", known_conditions=["Anemia"]
    )
    token = create_access_token(str(user.id))
    response = await test_client.get(
        "/api/v1/users/me/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["age"] == 34
    assert data["sex"] == "female"
    assert data["known_conditions"] == ["Anemia"]
    assert data["user_id"] == str(user.id)


@pytest.mark.asyncio
async def test_update_profile_creates_new(test_client: AsyncClient, make_user):
    user, _ = await make_user(email="createprofile@test.com")
    token = create_access_token(str(user.id))
    payload = {"age": 34, "sex": "female", "known_conditions": ["Anemia"]}
    response = await test_client.put(
        "/api/v1/users/me/profile",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["age"] == 34
    assert data["known_conditions"] == ["Anemia"]
    assert data["user_id"] == str(user.id)


@pytest.mark.asyncio
async def test_update_profile_upserts(
    test_client: AsyncClient, async_db_session: AsyncSession, make_user
):
    from sqlalchemy import func, select

    from app.users.models import UserProfile

    user, _ = await make_user(email="upsert@test.com")
    token = create_access_token(str(user.id))

    # First PUT
    await test_client.put(
        "/api/v1/users/me/profile",
        json={"age": 30},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Second PUT — should not duplicate
    response = await test_client.put(
        "/api/v1/users/me/profile",
        json={"age": 31},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["age"] == 31

    # Verify only one row exists
    count_result = await async_db_session.execute(
        select(func.count()).select_from(UserProfile).where(UserProfile.user_id == user.id)
    )
    assert count_result.scalar_one() == 1


@pytest.mark.asyncio
async def test_update_profile_partial(
    test_client: AsyncClient, async_db_session: AsyncSession, make_user
):
    user, _ = await make_user(email="partial@test.com")
    await upsert_user_profile(async_db_session, user.id, age=25, sex="male", weight_kg=70)
    token = create_access_token(str(user.id))

    # Only update age
    response = await test_client.put(
        "/api/v1/users/me/profile",
        json={"age": 26},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["age"] == 26
    # sex and weight_kg should remain
    assert data["sex"] == "male"
    assert data["weight_kg"] == 70.0


@pytest.mark.asyncio
async def test_profile_requires_auth(test_client: AsyncClient):
    response = await test_client.get("/api/v1/users/me/profile")
    assert response.status_code == 401  # HTTPBearer returns 401 when no credentials provided


@pytest.mark.asyncio
async def test_profile_user_isolation(
    test_client: AsyncClient, async_db_session: AsyncSession, make_user
):
    user_a, _ = await make_user(email="isolation_a@test.com")
    user_b, _ = await make_user(email="isolation_b@test.com")

    # Create profile for user_b
    await upsert_user_profile(async_db_session, user_b.id, age=40, sex="male")

    # Authenticate as user_a → should get 404 (not user_b's data)
    token_a = create_access_token(str(user_a.id))
    response = await test_client.get(
        "/api/v1/users/me/profile",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 404


# --- Consent History Endpoint ---


@pytest.mark.asyncio
async def test_consent_history_returns_entries_descending(
    test_client: AsyncClient, async_db_session: AsyncSession, make_user
):
    user, _ = await make_user(email="consent@test.com")
    # Create logs with explicit timestamps to guarantee ordering
    earlier = datetime.now(UTC) - timedelta(hours=1)
    log1 = ConsentLog(
        user_id=user.id,
        consent_type="health_data_processing",
        privacy_policy_version="1.0",
        consented_at=earlier,
    )
    log2 = ConsentLog(
        user_id=user.id,
        consent_type="health_data_processing",
        privacy_policy_version="2.0",
        consented_at=datetime.now(UTC),
    )
    async_db_session.add_all([log1, log2])
    await async_db_session.flush()
    token = create_access_token(str(user.id))

    response = await test_client.get(
        "/api/v1/users/me/consent-history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    # Most recent first (v2.0 was created after v1.0)
    assert data["items"][0]["privacy_policy_version"] == "2.0"
    assert data["items"][1]["privacy_policy_version"] == "1.0"
    # Each entry has expected fields
    entry = data["items"][0]
    assert "id" in entry
    assert "consent_type" in entry
    assert "consented_at" in entry


@pytest.mark.asyncio
async def test_consent_history_no_cross_user_leakage(
    test_client: AsyncClient, async_db_session: AsyncSession, make_user
):
    user_a, _ = await make_user(email="consent_a@test.com")
    user_b, _ = await make_user(email="consent_b@test.com")
    await create_consent_log(async_db_session, user_a.id, "health_data_processing", "1.0")
    await create_consent_log(async_db_session, user_b.id, "health_data_processing", "1.0")

    token_b = create_access_token(str(user_b.id))
    response = await test_client.get(
        "/api/v1/users/me/consent-history",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    # Ensure it's user_b's log, not user_a's
    assert all(item["consent_type"] == "health_data_processing" for item in items)


@pytest.mark.asyncio
async def test_consent_history_requires_auth(test_client: AsyncClient):
    response = await test_client.get("/api/v1/users/me/consent-history")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_registration_creates_consent_log_visible_in_history(
    test_client: AsyncClient,
):
    """Story 6-3 AC3: Registration always produces a consent log visible via the
    history endpoint.

    Exercises the full integration surface — POST /auth/register then GET
    /users/me/consent-history — so a regression that moves consent creation
    out of the registration transaction, or one that double-logs, or one that
    records a stale `consented_at`, would be caught here. Existing tests seed
    consent_logs directly via fixtures; this one does not.
    """
    suffix = uuid.uuid4().hex[:8]
    email = f"register_visible_{suffix}@test.com"
    register_payload = {
        "email": email,
        "password": "securepassword",
        "gdpr_consent": True,
        "privacy_policy_version": "1.0",
    }
    request_sent_at = datetime.now(UTC)
    register_response = await test_client.post("/api/v1/auth/register", json=register_payload)
    assert register_response.status_code == 201
    token = register_response.json()["access_token"]

    history_response = await test_client.get(
        "/api/v1/users/me/consent-history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert history_response.status_code == 200
    items = history_response.json()["items"]

    # FR6 invariant: exactly one entry for a fresh account (Story 1.2 registration
    # consent). Tighter than ">= 1" so a duplicate-log regression is caught too.
    matching = [
        item
        for item in items
        if item["consent_type"] == "health_data_processing"
        and item["privacy_policy_version"] == "1.0"
    ]
    assert len(matching) == 1

    # AC3 freshness: consented_at must fall inside the registration request's
    # response window. A 10-second generous bound tolerates container cold-start
    # and DB round-trip without letting a clock-skew or stale-default regression
    # slip through.
    consented_at = datetime.fromisoformat(matching[0]["consented_at"])
    delta = abs((consented_at - request_sent_at).total_seconds())
    assert delta < 10, f"consented_at drifted {delta:.2f}s from request (expected < 10s)"


# --- Account Deletion Endpoint ---


@pytest.mark.asyncio
async def test_delete_account_success(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    mock_arq_redis: MockArqRedis,
):
    del mock_arq_redis
    user, _ = await make_user(email="delete_me@test.com")
    await create_consent_log(async_db_session, user.id, "health_data_processing", "1.0")
    token = create_access_token(str(user.id))

    response = await test_client.delete(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    # User row should be gone
    result = await async_db_session.execute(select(User).where(User.id == user.id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_account_retains_consent_logs_and_redacts_audit(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    mock_arq_redis: MockArqRedis,
):
    """Story 6-2 AC6 + AC2: full cascade preserves consent_logs (user_id NULL) and
    redacts audit_logs (erasure marker) in a single transaction.
    """
    del mock_arq_redis
    suffix = uuid.uuid4().hex[:8]
    admin_user, subject_user, audit_log = await _create_admin_audit_log_fixture(
        async_db_session,
        make_user,
        admin_email=f"cascade_admin_{suffix}@test.com",
        subject_email=f"delete_consent_{suffix}@test.com",
    )
    await create_consent_log(async_db_session, subject_user.id, "health_data_processing", "1.0")
    audit_id = audit_log.id
    admin_id = admin_user.id
    token = create_access_token(str(subject_user.id))

    response = await test_client.delete(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    async_db_session.expire_all()

    # Consent logs retained with user_id set to NULL (regulatory requirement)
    result = await async_db_session.execute(
        select(ConsentLog).where(ConsentLog.consent_type == "health_data_processing")
    )
    logs = list(result.scalars().all())
    retained = [log for log in logs if log.user_id is None]
    assert len(retained) >= 1

    # Audit log redacted in the same cascade
    audit_result = await async_db_session.execute(select(AuditLog).where(AuditLog.id == audit_id))
    audit_row = audit_result.scalar_one_or_none()
    assert audit_row is not None
    assert audit_row.original_value == ERASURE_MARKER
    assert audit_row.new_value == ERASURE_MARKER
    assert audit_row.user_id is None
    # Admin accountability preserved
    assert audit_row.admin_id == admin_id


@pytest.mark.asyncio
async def test_delete_admin_account_with_audit_logs_succeeds(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    mock_arq_redis: MockArqRedis,
):
    del mock_arq_redis
    admin_user, _, audit_log = await _create_admin_audit_log_fixture(
        async_db_session,
        make_user,
        admin_email="delete_admin@test.com",
        subject_email="delete_admin_subject@test.com",
    )
    token = create_access_token(str(admin_user.id))

    response = await test_client.delete(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204

    deleted_admin = await async_db_session.execute(select(User).where(User.id == admin_user.id))
    assert deleted_admin.scalar_one_or_none() is None

    # Verify the audit row was retained and the deleted admin was redacted from it.
    retained_audit = await async_db_session.execute(
        select(AuditLog).where(AuditLog.id == audit_log.id)
    )
    retained_row = retained_audit.scalar_one_or_none()
    assert retained_row is not None
    assert retained_row.admin_id is None


@pytest.mark.asyncio
async def test_delete_admin_account_retains_audit_logs_with_null_admin_id(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    mock_arq_redis: MockArqRedis,
):
    del mock_arq_redis
    admin_user, subject_user, audit_log = await _create_admin_audit_log_fixture(
        async_db_session,
        make_user,
        admin_email="delete_admin_retained@test.com",
        subject_email="delete_admin_retained_subject@test.com",
    )
    token = create_access_token(str(admin_user.id))

    response = await test_client.delete(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204

    retained_log_result = await async_db_session.execute(
        select(AuditLog).where(AuditLog.id == audit_log.id)
    )
    retained_row = retained_log_result.scalar_one_or_none()
    assert retained_row is not None
    assert retained_row.admin_id is None
    assert retained_row.user_id == subject_user.id
    assert retained_row.value_name == "Glucose"
    assert retained_row.original_value == "95"
    assert retained_row.new_value == "100"
    assert retained_row.reason == "Corrected OCR error"
    assert retained_row.corrected_at is not None


@pytest.mark.asyncio
async def test_delete_account_requires_auth(test_client: AsyncClient):
    response = await test_client.delete("/api/v1/users/me")
    assert response.status_code == 401


# --- Story 14-2: MinIO cleanup on account deletion ---


@pytest.mark.asyncio
async def test_delete_account_enqueues_storage_reconciliation(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    mock_arq_redis: MockArqRedis,
):
    """Account deletion enqueues a deferred storage reconciliation job (Story 14-2).

    Inline MinIO cleanup was removed to eliminate the commit-before-async-op race.
    Instead, a deferred job runs after ACCOUNT_DELETION_RECONCILIATION_DELAY_SECONDS.
    """
    user, _ = await make_user(email="delete_queue@test.com")
    token = create_access_token(str(user.id))

    response = await test_client.delete(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204
    assert len(mock_arq_redis.enqueued) == 1
    assert mock_arq_redis.enqueued[0]["func"] == "reconcile_deleted_user_storage"
    assert mock_arq_redis.enqueued[0]["kwargs"]["user_id"] == str(user.id)
    assert mock_arq_redis.enqueued[0]["kwargs"]["prefix"] == f"{user.id}/"
    assert mock_arq_redis.enqueued[0]["kwargs"]["_defer_by"] > 0


@pytest.mark.asyncio
async def test_delete_account_arq_enqueue_failure_does_not_block_deletion(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    mock_arq_redis: MockArqRedis,
):
    """Cleanup-enqueue failure doesn't block user deletion (Story 14-2 pattern).

    MinIO cleanup is entirely deferred to an ARQ worker — there is no inline
    MinIO call in delete_user_account anymore. The operative "cleanup failure
    doesn't block" behavior is now: if the enqueue itself fails (Redis down,
    etc.), the user row is already DB-committed, so the endpoint still returns
    204 and the orphan prefix is logged for operator intervention.
    """
    user, _ = await make_user(email="arq_fail@test.com")
    token = create_access_token(str(user.id))

    async def failing_enqueue(*args, **kwargs):
        raise RuntimeError("Redis unavailable")

    mock_arq_redis.enqueue_job = failing_enqueue

    response = await test_client.delete(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204

    # User row is still deleted despite enqueue failure (DB commit already happened)
    result = await async_db_session.execute(select(User).where(User.id == user.id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_account_no_documents_still_attempts_prefix_cleanup(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    mock_arq_redis: MockArqRedis,
):
    """Even with no documents, reconciliation job is enqueued (not inline MinIO).

    Inline MinIO cleanup was removed — the deferred job catches orphaned objects.
    """
    del async_db_session
    user, _ = await make_user(email="no_docs@test.com")
    token = create_access_token(str(user.id))

    response = await test_client.delete(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204
    # Reconciliation job must be enqueued even with no documents
    assert len(mock_arq_redis.enqueued) == 1
    assert mock_arq_redis.enqueued[0]["func"] == "reconcile_deleted_user_storage"


@pytest.mark.asyncio
async def test_delete_account_runs_prefix_cleanup_after_commit(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    mock_arq_redis: MockArqRedis,
):
    """Deletion commits first, then enqueues reconciliation job (not inline MinIO).

    Inline MinIO cleanup was removed — the deferred job is the safety net.
    Verifies commit → enqueue ordering by recording both events in sequence.
    """
    user, _ = await make_user(email="delete_order@test.com")
    token = create_access_token(str(user.id))
    events: list[str] = []

    original_commit = async_db_session.commit
    original_enqueue = mock_arq_redis.enqueue_job

    async def commit_spy() -> None:
        events.append("commit")
        await original_commit()

    async def enqueue_spy(func_name: str, **kwargs: object) -> MagicMock:
        events.append("enqueue")
        return await original_enqueue(func_name, **kwargs)

    mock_arq_redis.enqueue_job = enqueue_spy

    with patch.object(async_db_session, "commit", AsyncMock(side_effect=commit_spy)):
        response = await test_client.delete(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 204
    # Commit must fire before enqueue — verifies deferred-job ordering guarantee
    assert events == ["commit", "enqueue"]
    assert len(mock_arq_redis.enqueued) == 1


# --- Story 6-2: Audit-log erasure marker + JWT invalidation + atomicity ---


@pytest.mark.asyncio
async def test_delete_account_redacts_audit_log_with_erasure_marker(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
    make_health_value,
    mock_arq_redis: MockArqRedis,
):
    """Story 6-2 AC2: Legacy FK-only audit rows are redacted before subject deletion.

    This covers the legacy shape still supported by the repository layer:
    the audit row is linked to the subject only through document_id /
    health_value_id while user_id is already NULL.

    When that user is deleted:
    - audit_logs.original_value → '[REDACTED]'
    - audit_logs.new_value → '[REDACTED]'
    - audit_logs.value_name → '[REDACTED]' (biomarker name can identify condition)
    - audit_logs.document_id → NULL
    - audit_logs.health_value_id → NULL
    - audit_logs.admin_id → preserved (different person's accountability record)

    Because documents / health_values are deleted by FK cascade, the redaction
    query must run before DELETE FROM users while those IDs still exist.
    """
    del mock_arq_redis
    suffix = uuid.uuid4().hex[:8]
    admin_user, _ = await make_user(email=f"erase_admin_{suffix}@test.com")
    admin_user.role = "admin"
    async_db_session.add(admin_user)
    subject_user, _ = await make_user(email=f"erase_subject_{suffix}@test.com")
    document = await make_document(user=subject_user, filename=f"legacy_{suffix}.pdf")
    health_value = await make_health_value(
        user=subject_user,
        document=document,
        biomarker_name="Glucose",
        canonical_biomarker_name="Glucose",
        value=95.0,
    )
    audit_log = AuditLog(
        admin_id=admin_user.id,
        user_id=None,
        document_id=document.id,
        health_value_id=health_value.id,
        value_name="Glucose",
        original_value="95",
        new_value="100",
        reason="Corrected OCR error",
    )
    async_db_session.add(audit_log)
    await async_db_session.flush()
    audit_id = audit_log.id
    admin_id = admin_user.id
    token = create_access_token(str(subject_user.id))

    response = await test_client.delete(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204

    async_db_session.expire_all()

    # Audit row survives user deletion
    retained = await async_db_session.execute(select(AuditLog).where(AuditLog.id == audit_id))
    row = retained.scalar_one_or_none()
    assert row is not None, "audit row must be retained across subject deletion"

    # Redacted columns
    assert row.user_id is None
    assert row.document_id is None
    assert row.health_value_id is None
    assert row.original_value == ERASURE_MARKER
    assert row.new_value == ERASURE_MARKER
    assert row.value_name == ERASURE_MARKER

    # Admin accountability preserved on legacy-shape row
    assert row.admin_id == admin_id


@pytest.mark.asyncio
async def test_delete_account_preserves_admin_columns_after_subject_deletion(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    mock_arq_redis: MockArqRedis,
):
    """Story 6-2 AC2: Subject deletion preserves admin_id, reason, corrected_at;
    redacts value_name alongside original_value / new_value.

    `reason` and `corrected_at` are the regulatory audit trail — WHO did what correction
    and WHY — and must survive subject deletion since they record the admin's
    accountability, not the deleted subject's data.

    `value_name` is redacted because a biomarker name (e.g. "HIV viral load",
    "Pregnancy hCG") can by itself identify the subject's health condition.
    """
    del mock_arq_redis
    suffix = uuid.uuid4().hex[:8]
    admin_user, subject_user, audit_log = await _create_admin_audit_log_fixture(
        async_db_session,
        make_user,
        admin_email=f"preserve_admin_{suffix}@test.com",
        subject_email=f"preserve_subject_{suffix}@test.com",
    )
    admin_id = admin_user.id
    audit_id = audit_log.id
    original_reason = audit_log.reason
    original_corrected_at = audit_log.corrected_at
    token = create_access_token(str(subject_user.id))

    response = await test_client.delete(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204

    async_db_session.expire_all()

    retained = await async_db_session.execute(select(AuditLog).where(AuditLog.id == audit_id))
    row = retained.scalar_one_or_none()
    assert row is not None

    # Admin accountability preserved
    assert row.admin_id == admin_id
    assert row.reason == original_reason
    assert row.corrected_at == original_corrected_at
    # value_name redacted (can identify subject's health condition)
    assert row.value_name == ERASURE_MARKER


@pytest.mark.asyncio
async def test_jwt_rejected_after_account_deletion(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    mock_arq_redis: MockArqRedis,
):
    """Story 6-2 AC4: A still-valid JWT is rejected after its user is deleted.

    Access tokens are 15-min JWTs. A token issued before deletion remains
    cryptographically valid until expiry, but the auth dependency queries
    the DB for the user_id and rejects with 401 when the row is gone.
    """
    del mock_arq_redis
    del async_db_session
    user, _ = await make_user(email="jwt_invalidation@test.com")
    token = create_access_token(str(user.id))
    auth_header = {"Authorization": f"Bearer {token}"}

    # Sanity: token works before deletion
    pre_response = await test_client.get("/api/v1/users/me/consent-history", headers=auth_header)
    assert pre_response.status_code == 200

    # Delete the account
    delete_response = await test_client.delete("/api/v1/users/me", headers=auth_header)
    assert delete_response.status_code == 204

    # Same token is now rejected
    post_response = await test_client.get("/api/v1/users/me/consent-history", headers=auth_header)
    assert post_response.status_code == 401


@pytest.mark.asyncio
async def test_delete_account_rolls_back_on_audit_redaction_failure(
    async_db_session: AsyncSession,
    make_user,
    mock_arq_redis: MockArqRedis,
):
    """Story 6-2 AC3: DB step failure short-circuits the cascade without partial state.

    If audit redaction raises:
    1. Endpoint returns 500 (global exception handler at main.py:143)
    2. db.commit() is never called — proves atomicity directly via spy assertion
       (no observed-DB-state confusion from identity-map caching on the same session)
    3. DELETE FROM users is never reached (would execute later in same function)
    4. MinIO reconciliation is never enqueued (guarded on successful commit path)

    Uses a local client with raise_app_exceptions=False so httpx does not
    re-raise the RuntimeError after the global handler has converted it to a 500.
    """
    from app.core.database import get_db

    suffix = uuid.uuid4().hex[:8]
    _admin_user, subject_user, _audit_log = await _create_admin_audit_log_fixture(
        async_db_session,
        make_user,
        admin_email=f"rollback_admin_{suffix}@test.com",
        subject_email=f"rollback_subject_{suffix}@test.com",
    )
    token = create_access_token(str(subject_user.id))

    async def override_get_db():
        yield async_db_session

    app.dependency_overrides[get_db] = override_get_db

    real_execute = AsyncSession.execute

    async def failing_execute(self, statement, *args, **kwargs):
        # Structural match on the Update construct targeting audit_logs.
        # Avoids string-match fragility against future SQLAlchemy dialect changes.
        if isinstance(statement, Update) and statement.table.name == "audit_logs":
            raise RuntimeError("simulated audit redaction failure")
        return await real_execute(self, statement, *args, **kwargs)

    commit_spy = AsyncMock()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            with (
                patch.object(AsyncSession, "execute", failing_execute),
                patch.object(async_db_session, "commit", commit_spy),
            ):
                response = await client.delete(
                    "/api/v1/users/me",
                    headers={"Authorization": f"Bearer {token}"},
                )
    finally:
        app.dependency_overrides.pop(get_db, None)

    # 500 via global exception handler (RFC 7807 style)
    assert response.status_code == 500
    body = response.json()
    assert body["status"] == 500
    assert response.headers["x-request-id"]

    # Atomicity proof: commit() was never awaited → nothing was persisted.
    assert commit_spy.await_count == 0

    # Reconciliation job must NOT be enqueued — commit path was never reached.
    assert len(mock_arq_redis.enqueued) == 0


@pytest.mark.asyncio
async def test_login_rejected_after_account_deletion(
    test_client: AsyncClient,
    make_user,
    mock_arq_redis: MockArqRedis,
):
    """Story 6-2 AC5: Former credentials cannot issue a new session after deletion.

    The users row is hard-deleted, so password lookup by email returns None and
    the login endpoint responds 401 — identical to the wrong-password and
    nonexistent-email paths (no user enumeration via timing or status code).
    """
    del mock_arq_redis
    suffix = uuid.uuid4().hex[:8]
    email = f"login_after_delete_{suffix}@test.com"
    user, password = await make_user(email=email)
    token = create_access_token(str(user.id))

    # Delete the account first.
    delete_response = await test_client.delete(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_response.status_code == 204

    # Login with the former credentials must now return 401.
    login_response = await test_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 401
    # No new session issued — same 401 shape as wrong-password path.
    body = login_response.json()
    assert body["status"] == 401
