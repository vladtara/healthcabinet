"""
Tests for admin user management and flagged value report endpoints (Story 5.3).

Covers: GET /admin/users, GET /admin/users/{id}, PATCH /admin/users/{id}/status,
GET /admin/flags, POST /admin/flags/{id}/review, plus suspension enforcement in
login, refresh, and bearer auth.

Uses real database — no DB mocking per project rules.
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token
from app.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def admin_client(async_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Test client with DB override."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield async_db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def admin_headers(user: User) -> dict[str, str]:
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


def user_headers(user: User) -> dict[str, str]:
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


async def _make_admin(make_user, async_db_session: AsyncSession, email: str) -> User:
    admin_user, _ = await make_user(email=email)
    admin_user.role = "admin"
    async_db_session.add(admin_user)
    await async_db_session.flush()
    return admin_user


# ===========================================================================
# Tests: GET /admin/users
# ===========================================================================


class TestAdminUserList:
    """Admin user list endpoint tests."""

    async def test_returns_users_with_upload_counts(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
        make_document,
    ):
        """User list includes upload_count per user and excludes admin accounts."""
        admin = await _make_admin(make_user, async_db_session, "ul_admin@example.com")
        user1, _ = await make_user(email="ul_user1@example.com")
        user2, _ = await make_user(email="ul_user2@example.com")

        await make_document(user=user1, filename="a.pdf")
        await make_document(user=user1, filename="b.pdf")
        await make_document(user=user2, filename="c.pdf")

        resp = await admin_client.get("/api/v1/admin/users", headers=admin_headers(admin))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2  # excludes admin

        by_id = {item["user_id"]: item for item in data["items"]}
        assert by_id[str(user1.id)]["upload_count"] == 2
        assert by_id[str(user2.id)]["upload_count"] == 1
        # Admin user should NOT appear
        assert str(admin.id) not in by_id
        # T2: Health data fields must NOT leak through user list
        for item in data["items"]:
            for forbidden in (
                "health_values",
                "documents",
                "ai_memories",
                "user_profiles",
                "interpretations",
                "biomarker_values",
                "extracted_values",
            ):
                assert forbidden not in item

    async def test_search_by_email(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        """Search query filters users by email substring."""
        admin = await _make_admin(make_user, async_db_session, "search_admin@example.com")
        user_a, _ = await make_user(email="alice@example.com")
        _user_b, _ = await make_user(email="bob@example.com")

        resp = await admin_client.get(
            "/api/v1/admin/users", headers=admin_headers(admin), params={"q": "alice"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["email"] == "alice@example.com"

    async def test_search_by_user_id(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        """Search query filters users by UUID substring."""
        admin = await _make_admin(make_user, async_db_session, "sid_admin@example.com")
        user_a, _ = await make_user(email="sid_user@example.com")
        _user_b, _ = await make_user(email="sid_other@example.com")

        # Use first 8 chars of UUID as search
        partial_id = str(user_a.id)[:8]
        resp = await admin_client.get(
            "/api/v1/admin/users", headers=admin_headers(admin), params={"q": partial_id}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert any(item["user_id"] == str(user_a.id) for item in data["items"])
        # T11: Non-matching user should be absent
        assert not any(item["user_id"] == str(_user_b.id) for item in data["items"])

    async def test_search_treats_like_wildcards_as_literals(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        """Search should not treat user-provided % or _ as SQL wildcards."""
        admin = await _make_admin(make_user, async_db_session, "literal_admin@example.com")
        target_user, _ = await make_user(email="ann_100%match@example.com")
        _other_user, _ = await make_user(email="annx100zmatch@example.com")

        resp = await admin_client.get(
            "/api/v1/admin/users",
            headers=admin_headers(admin),
            params={"q": "ann_100%match"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["user_id"] == str(target_user.id)

    async def test_empty_list_returns_zero(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        """No regular users → empty list."""
        admin = await _make_admin(make_user, async_db_session, "empty_admin@example.com")

        resp = await admin_client.get("/api/v1/admin/users", headers=admin_headers(admin))
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0


# ===========================================================================
# Tests: GET /admin/users/{user_id}
# ===========================================================================


class TestAdminUserDetail:
    """Admin user detail endpoint tests."""

    async def test_returns_user_metadata(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
        make_document,
    ):
        """Detail returns account metadata with upload count and no health data."""
        admin = await _make_admin(make_user, async_db_session, "det_admin@example.com")
        user, _ = await make_user(email="det_user@example.com")
        await make_document(user=user, filename="x.pdf")

        resp = await admin_client.get(
            f"/api/v1/admin/users/{user.id}", headers=admin_headers(admin)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == str(user.id)
        assert data["email"] == "det_user@example.com"
        assert data["upload_count"] == 1
        assert data["account_status"] == "active"
        assert "registration_date" in data
        assert "last_login" in data
        # T2: No health data fields in detail
        for forbidden in (
            "health_values",
            "documents",
            "ai_memories",
            "user_profiles",
            "interpretations",
            "biomarker_values",
            "extracted_values",
        ):
            assert forbidden not in data

    async def test_nonexistent_user_returns_404(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        admin = await _make_admin(make_user, async_db_session, "nf_admin@example.com")
        fake_id = uuid.uuid4()

        resp = await admin_client.get(
            f"/api/v1/admin/users/{fake_id}", headers=admin_headers(admin)
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "User not found"

    async def test_admin_user_id_returns_404(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        """Looking up another admin's ID returns 404 (scoped to role=user)."""
        admin = await _make_admin(make_user, async_db_session, "adm1@example.com")
        other_admin = await _make_admin(make_user, async_db_session, "adm2@example.com")

        resp = await admin_client.get(
            f"/api/v1/admin/users/{other_admin.id}", headers=admin_headers(admin)
        )
        assert resp.status_code == 404


# ===========================================================================
# Tests: PATCH /admin/users/{user_id}/status
# ===========================================================================


class TestAdminUserStatusUpdate:
    """Suspend/reactivate user account tests."""

    async def test_suspend_user(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        admin = await _make_admin(make_user, async_db_session, "susp_admin@example.com")
        user, _ = await make_user(email="susp_user@example.com")

        resp = await admin_client.patch(
            f"/api/v1/admin/users/{user.id}/status",
            headers=admin_headers(admin),
            json={"account_status": "suspended"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["account_status"] == "suspended"
        assert data["user_id"] == str(user.id)

    async def test_reactivate_user(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        admin = await _make_admin(make_user, async_db_session, "react_admin@example.com")
        user, _ = await make_user(email="react_user@example.com")
        user.account_status = "suspended"
        async_db_session.add(user)
        await async_db_session.flush()

        resp = await admin_client.patch(
            f"/api/v1/admin/users/{user.id}/status",
            headers=admin_headers(admin),
            json={"account_status": "active"},
        )
        assert resp.status_code == 200
        assert resp.json()["account_status"] == "active"

    async def test_cannot_suspend_admin(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        """Admins cannot be suspended via this endpoint (scoped to role=user)."""
        admin = await _make_admin(make_user, async_db_session, "ca_admin@example.com")
        other_admin = await _make_admin(make_user, async_db_session, "ca_target@example.com")

        resp = await admin_client.patch(
            f"/api/v1/admin/users/{other_admin.id}/status",
            headers=admin_headers(admin),
            json={"account_status": "suspended"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "User not found"

    async def test_nonexistent_user_returns_404(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        admin = await _make_admin(make_user, async_db_session, "nf_status_admin@example.com")
        fake_id = uuid.uuid4()

        resp = await admin_client.patch(
            f"/api/v1/admin/users/{fake_id}/status",
            headers=admin_headers(admin),
            json={"account_status": "suspended"},
        )
        assert resp.status_code == 404

    async def test_invalid_status_returns_422(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        admin = await _make_admin(make_user, async_db_session, "inv_admin@example.com")
        user, _ = await make_user(email="inv_user@example.com")

        resp = await admin_client.patch(
            f"/api/v1/admin/users/{user.id}/status",
            headers=admin_headers(admin),
            json={"account_status": "banned"},
        )
        assert resp.status_code == 422


# ===========================================================================
# Tests: Suspension enforcement (login / refresh / bearer)
# ===========================================================================


class TestSuspensionEnforcement:
    """Suspended users are blocked at login, refresh, and bearer auth."""

    async def test_suspended_user_login_returns_403(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        """Suspended user with valid creds gets 403 on login."""
        user, password = await make_user(email="susp_login@example.com")
        user.account_status = "suspended"
        async_db_session.add(user)
        await async_db_session.flush()

        resp = await admin_client.post(
            "/api/v1/auth/login",
            json={"email": "susp_login@example.com", "password": password},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Account is suspended"

    async def test_suspended_user_refresh_returns_401(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        """Suspended user with valid refresh token gets 403 + cookie cleared."""
        user, _ = await make_user(email="susp_refresh@example.com")
        refresh_token = create_refresh_token(str(user.id))

        # Suspend after creating token
        user.account_status = "suspended"
        async_db_session.add(user)
        await async_db_session.flush()

        resp = await admin_client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": refresh_token},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Account is suspended"
        # T7: Cookie must be cleared
        set_cookie = resp.headers.get("set-cookie", "").lower()
        assert "refresh_token=" in set_cookie
        assert "max-age=0" in set_cookie
        assert "path=/api/v1/auth/refresh" in set_cookie

    async def test_suspended_user_bearer_returns_403(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        """Suspended user with valid access token gets 403 on any protected endpoint."""
        user, _ = await make_user(email="susp_bearer@example.com")
        token = create_access_token(str(user.id))

        user.account_status = "suspended"
        async_db_session.add(user)
        await async_db_session.flush()

        resp = await admin_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Account is suspended"

    async def test_active_user_login_sets_last_login(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        """Successful login sets last_login_at on the user row."""
        user, password = await make_user(email="llt_user@example.com")
        assert user.last_login_at is None

        resp = await admin_client.post(
            "/api/v1/auth/login",
            json={"email": "llt_user@example.com", "password": password},
        )
        assert resp.status_code == 200

        await async_db_session.refresh(user)
        assert user.last_login_at is not None

    async def test_reactivation_restores_login(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        """T3: Suspend → login fails 403 → reactivate → login succeeds."""
        admin = await _make_admin(make_user, async_db_session, "rt_admin@example.com")
        user, password = await make_user(email="rt_user@example.com")

        # Suspend
        user.account_status = "suspended"
        async_db_session.add(user)
        await async_db_session.flush()

        # Login should fail
        resp = await admin_client.post(
            "/api/v1/auth/login",
            json={"email": "rt_user@example.com", "password": password},
        )
        assert resp.status_code == 403

        # Reactivate via admin endpoint
        resp = await admin_client.patch(
            f"/api/v1/admin/users/{user.id}/status",
            headers=admin_headers(admin),
            json={"account_status": "active"},
        )
        assert resp.status_code == 200

        # Login should succeed now
        resp = await admin_client.post(
            "/api/v1/auth/login",
            json={"email": "rt_user@example.com", "password": password},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_refresh_does_not_update_last_login(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        """T6: last_login_at is unchanged after a token refresh (only set on credential login)."""
        user, password = await make_user(email="rll_user@example.com")

        # Login to set last_login_at
        resp = await admin_client.post(
            "/api/v1/auth/login",
            json={"email": "rll_user@example.com", "password": password},
        )
        assert resp.status_code == 200

        await async_db_session.refresh(user)
        login_time = user.last_login_at
        assert login_time is not None

        # Refresh
        refresh_token = create_refresh_token(str(user.id))
        resp = await admin_client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200

        await async_db_session.refresh(user)
        assert user.last_login_at == login_time


# ===========================================================================
# Tests: GET /admin/flags
# ===========================================================================


class TestFlaggedReportList:
    """Flagged value report listing tests."""

    async def test_returns_unreviewed_flags(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
        make_document,
        make_health_value,
    ):
        """Only unreviewed flagged values appear in the list."""
        admin = await _make_admin(make_user, async_db_session, "fl_admin@example.com")
        user, _ = await make_user(email="fl_user@example.com")
        doc = await make_document(user=user, status="completed")

        # Unreviewed flagged value
        hv_flagged = await make_health_value(
            user=user,
            document=doc,
            value=999.0,
            is_flagged=True,
            biomarker_name="Glucose",
            canonical_biomarker_name="glucose",
        )
        # Set flagged_at manually
        hv_flagged.flagged_at = datetime.now(UTC)
        async_db_session.add(hv_flagged)
        await async_db_session.flush()

        # Reviewed flagged value — should NOT appear
        hv_reviewed = await make_health_value(
            user=user,
            document=doc,
            value=888.0,
            is_flagged=True,
            biomarker_name="Potassium",
            canonical_biomarker_name="potassium",
        )
        hv_reviewed.flagged_at = datetime.now(UTC)
        hv_reviewed.flag_reviewed_at = datetime.now(UTC)
        hv_reviewed.flag_reviewed_by_admin_id = admin.id
        async_db_session.add(hv_reviewed)
        await async_db_session.flush()

        # Non-flagged value — should NOT appear
        await make_health_value(
            user=user,
            document=doc,
            value=5.0,
            biomarker_name="Cholesterol",
            canonical_biomarker_name="cholesterol_total",
        )

        resp = await admin_client.get("/api/v1/admin/flags", headers=admin_headers(admin))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["health_value_id"] == str(hv_flagged.id)
        assert data["items"][0]["value_name"] == "glucose"
        assert data["items"][0]["flagged_value"] == 999.0

    async def test_empty_flags_returns_zero(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        admin = await _make_admin(make_user, async_db_session, "ef_admin@example.com")

        resp = await admin_client.get("/api/v1/admin/flags", headers=admin_headers(admin))
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_corrupt_flagged_value_is_skipped_with_warning(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
        make_document,
        make_health_value,
    ):
        """Corrupt flagged values are skipped (logged) but don't crash the endpoint."""
        admin = await _make_admin(make_user, async_db_session, "corrupt_admin@example.com")
        user, _ = await make_user(email="corrupt_user@example.com")
        doc = await make_document(user=user, status="completed")
        hv = await make_health_value(
            user=user,
            document=doc,
            value=999.0,
            is_flagged=True,
            biomarker_name="Glucose",
            canonical_biomarker_name="glucose",
        )
        hv.flagged_at = datetime.now(UTC)
        hv.value_encrypted = b"definitely-not-valid-ciphertext"
        async_db_session.add(hv)
        await async_db_session.flush()

        resp = await admin_client.get("/api/v1/admin/flags", headers=admin_headers(admin))
        assert resp.status_code == 200
        data = resp.json()
        # Corrupt value is skipped, not returned
        assert data["total"] == 0
        assert data["items"] == []


# ===========================================================================
# Tests: POST /admin/flags/{health_value_id}/review
# ===========================================================================


class TestMarkFlagReviewed:
    """Flag review endpoint tests."""

    async def test_mark_flag_reviewed(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
        make_document,
        make_health_value,
    ):
        admin = await _make_admin(make_user, async_db_session, "mr_admin@example.com")
        user, _ = await make_user(email="mr_user@example.com")
        doc = await make_document(user=user, status="completed")
        hv = await make_health_value(
            user=user,
            document=doc,
            value=999.0,
            is_flagged=True,
            biomarker_name="Glucose",
            canonical_biomarker_name="glucose",
        )
        hv.flagged_at = datetime.now(UTC)
        async_db_session.add(hv)
        await async_db_session.flush()

        resp = await admin_client.post(
            f"/api/v1/admin/flags/{hv.id}/review", headers=admin_headers(admin)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["health_value_id"] == str(hv.id)
        assert "reviewed_at" in data

        # Verify DB state
        await async_db_session.refresh(hv)
        assert hv.flag_reviewed_at is not None
        assert hv.flag_reviewed_by_admin_id == admin.id
        # T1: is_flagged must remain True after review
        assert hv.is_flagged is True

    async def test_idempotent_review(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
        make_document,
        make_health_value,
    ):
        """Reviewing the same flag twice is idempotent — no error, same reviewed_at."""
        admin = await _make_admin(make_user, async_db_session, "idem_admin@example.com")
        user, _ = await make_user(email="idem_user@example.com")
        doc = await make_document(user=user, status="completed")
        hv = await make_health_value(
            user=user,
            document=doc,
            value=999.0,
            is_flagged=True,
            biomarker_name="Glucose",
            canonical_biomarker_name="glucose",
        )
        hv.flagged_at = datetime.now(UTC)
        async_db_session.add(hv)
        await async_db_session.flush()

        resp1 = await admin_client.post(
            f"/api/v1/admin/flags/{hv.id}/review", headers=admin_headers(admin)
        )
        assert resp1.status_code == 200
        first_reviewed_at = resp1.json()["reviewed_at"]

        resp2 = await admin_client.post(
            f"/api/v1/admin/flags/{hv.id}/review", headers=admin_headers(admin)
        )
        assert resp2.status_code == 200
        assert resp2.json()["reviewed_at"] == first_reviewed_at

    async def test_review_nonexistent_flag_returns_404(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        admin = await _make_admin(make_user, async_db_session, "nf_flag_admin@example.com")
        fake_id = uuid.uuid4()

        resp = await admin_client.post(
            f"/api/v1/admin/flags/{fake_id}/review", headers=admin_headers(admin)
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Flagged value not found"

    async def test_review_non_flagged_value_returns_404(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
        make_document,
        make_health_value,
    ):
        """Trying to review a non-flagged health value returns 404."""
        admin = await _make_admin(make_user, async_db_session, "nfl_admin@example.com")
        user, _ = await make_user(email="nfl_user@example.com")
        doc = await make_document(user=user, status="completed")
        hv = await make_health_value(
            user=user,
            document=doc,
            value=5.0,
            is_flagged=False,
        )

        resp = await admin_client.post(
            f"/api/v1/admin/flags/{hv.id}/review", headers=admin_headers(admin)
        )
        assert resp.status_code == 404


# ===========================================================================
# Tests: Error queue excludes reviewed flags
# ===========================================================================


class TestErrorQueueExcludesReviewedFlags:
    """Reviewed flags no longer keep documents in the error queue."""

    async def test_reviewed_flag_excluded_from_queue(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
        make_document,
        make_health_value,
    ):
        """Document with only reviewed-flagged values should NOT appear in error queue."""
        admin = await _make_admin(make_user, async_db_session, "eq_admin@example.com")
        user, _ = await make_user(email="eq_user@example.com")

        # Document with one flagged value (reviewed)
        doc = await make_document(user=user, status="completed", filename="reviewed_flag.pdf")
        hv = await make_health_value(
            user=user,
            document=doc,
            value=999.0,
            confidence=0.95,
            is_flagged=True,
            biomarker_name="Glucose",
            canonical_biomarker_name="glucose",
        )
        hv.flagged_at = datetime.now(UTC)
        hv.flag_reviewed_at = datetime.now(UTC)
        hv.flag_reviewed_by_admin_id = admin.id
        async_db_session.add(hv)
        await async_db_session.flush()

        resp = await admin_client.get("/api/v1/admin/queue", headers=admin_headers(admin))
        assert resp.status_code == 200
        data = resp.json()
        doc_ids = {item["document_id"] for item in data["items"]}
        assert str(doc.id) not in doc_ids

    async def test_unreviewed_flag_still_in_queue(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
        make_document,
        make_health_value,
    ):
        """Document with unreviewed-flagged value STILL appears in error queue."""
        admin = await _make_admin(make_user, async_db_session, "eq2_admin@example.com")
        user, _ = await make_user(email="eq2_user@example.com")

        doc = await make_document(user=user, status="completed", filename="unreviewed_flag.pdf")
        hv = await make_health_value(
            user=user,
            document=doc,
            value=999.0,
            confidence=0.95,
            is_flagged=True,
            biomarker_name="Glucose",
            canonical_biomarker_name="glucose",
        )
        hv.flagged_at = datetime.now(UTC)
        async_db_session.add(hv)
        await async_db_session.flush()

        resp = await admin_client.get("/api/v1/admin/queue", headers=admin_headers(admin))
        assert resp.status_code == 200
        data = resp.json()
        doc_ids = {item["document_id"] for item in data["items"]}
        assert str(doc.id) in doc_ids


# ===========================================================================
# Tests: Auth — non-admin / unauthenticated
# ===========================================================================


class TestAdminAuthGuards:
    """Non-admin and unauthenticated requests are rejected."""

    async def test_non_admin_403_on_user_list(self, admin_client: AsyncClient, make_user):
        user, _ = await make_user(email="reg_ul@example.com")
        resp = await admin_client.get("/api/v1/admin/users", headers=user_headers(user))
        assert resp.status_code == 403

    async def test_non_admin_403_on_user_detail(self, admin_client: AsyncClient, make_user):
        user, _ = await make_user(email="reg_ud@example.com")
        resp = await admin_client.get(f"/api/v1/admin/users/{user.id}", headers=user_headers(user))
        assert resp.status_code == 403

    async def test_non_admin_403_on_status_update(self, admin_client: AsyncClient, make_user):
        user, _ = await make_user(email="reg_su@example.com")
        resp = await admin_client.patch(
            f"/api/v1/admin/users/{user.id}/status",
            headers=user_headers(user),
            json={"account_status": "suspended"},
        )
        assert resp.status_code == 403

    async def test_non_admin_403_on_flags(self, admin_client: AsyncClient, make_user):
        user, _ = await make_user(email="reg_fl@example.com")
        resp = await admin_client.get("/api/v1/admin/flags", headers=user_headers(user))
        assert resp.status_code == 403

    async def test_non_admin_403_on_flag_review(self, admin_client: AsyncClient, make_user):
        user, _ = await make_user(email="reg_fr@example.com")
        fake_id = uuid.uuid4()
        resp = await admin_client.post(
            f"/api/v1/admin/flags/{fake_id}/review", headers=user_headers(user)
        )
        assert resp.status_code == 403

    async def test_no_jwt_401_on_user_list(self, admin_client: AsyncClient):
        resp = await admin_client.get("/api/v1/admin/users")
        assert resp.status_code == 401

    async def test_no_jwt_401_on_flags(self, admin_client: AsyncClient):
        resp = await admin_client.get("/api/v1/admin/flags")
        assert resp.status_code == 401

    async def test_no_jwt_401_on_flag_review(self, admin_client: AsyncClient):
        fake_id = uuid.uuid4()
        resp = await admin_client.post(f"/api/v1/admin/flags/{fake_id}/review")
        assert resp.status_code == 401


# ===========================================================================
# Tests: POST /admin/users/{id}/revoke-sessions
# ===========================================================================


class TestAdminRevokeSessions:
    """Admin-initiated session revocation tests.

    Revocation invalidates every JWT (access + refresh) whose iat is strictly before
    users.tokens_invalid_before, without changing account_status. Unlike suspension,
    revoked users can log in again immediately and receive fresh working tokens.
    """

    async def test_revoke_rejects_existing_access_token(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        admin = await _make_admin(make_user, async_db_session, "rev_a_admin@example.com")
        user, _ = await make_user(email="rev_a_user@example.com")
        # Backdate iat so the revocation cutoff (now, floored to second) is strictly
        # after this token. A helper would hide the claim shape; the test documents it.
        import jwt as _jwt

        from app.core.config import settings as _settings
        from app.core.security import ALGORITHM

        past = datetime.now(UTC) - timedelta(seconds=5)
        pre_token = _jwt.encode(
            {
                "sub": str(user.id),
                "iat": past,
                "exp": past + timedelta(minutes=15),
                "type": "access",
            },
            _settings.SECRET_KEY,
            algorithm=ALGORITHM,
        )

        # Pre-revoke: token works
        resp = await admin_client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {pre_token}"}
        )
        assert resp.status_code == 200

        # Admin revokes sessions
        resp = await admin_client.post(
            f"/api/v1/admin/users/{user.id}/revoke-sessions",
            headers=admin_headers(admin),
        )
        assert resp.status_code == 200
        assert resp.json()["user_id"] == str(user.id)

        # Old token now rejected
        resp = await admin_client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {pre_token}"}
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Session has been revoked"

    async def test_revoke_rejects_existing_refresh_token(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        admin = await _make_admin(make_user, async_db_session, "rev_r_admin@example.com")
        user, _ = await make_user(email="rev_r_user@example.com")
        import jwt as _jwt

        from app.core.config import settings as _settings
        from app.core.security import ALGORITHM

        past = datetime.now(UTC) - timedelta(seconds=5)
        old_refresh = _jwt.encode(
            {
                "sub": str(user.id),
                "iat": past,
                "exp": past + timedelta(days=30),
                "type": "refresh",
            },
            _settings.SECRET_KEY,
            algorithm=ALGORITHM,
        )

        resp = await admin_client.post(
            f"/api/v1/admin/users/{user.id}/revoke-sessions",
            headers=admin_headers(admin),
        )
        assert resp.status_code == 200

        # Old refresh token rejected; cookie-clear header attached so browsers drop it.
        resp = await admin_client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": old_refresh},
        )
        assert resp.status_code == 401
        set_cookie = resp.headers.get("set-cookie", "").lower()
        assert "refresh_token=" in set_cookie
        assert "max-age=0" in set_cookie

    async def test_revoke_allows_fresh_login(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        """Unlike suspension, revocation leaves the account active — the user can log in."""
        admin = await _make_admin(make_user, async_db_session, "rev_fl_admin@example.com")
        user, password = await make_user(email="rev_fl_user@example.com")

        resp = await admin_client.post(
            f"/api/v1/admin/users/{user.id}/revoke-sessions",
            headers=admin_headers(admin),
        )
        assert resp.status_code == 200

        # Fresh login succeeds and returns a working token.
        resp = await admin_client.post(
            "/api/v1/auth/login",
            json={"email": "rev_fl_user@example.com", "password": password},
        )
        assert resp.status_code == 200
        new_token = resp.json()["access_token"]

        resp = await admin_client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {new_token}"}
        )
        assert resp.status_code == 200

    async def test_revoke_cannot_target_admin(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        """Repository scopes revoke to role='user' — admins cannot be revoked here.

        Asserting only the 404 is not enough: a regression that drops the role='user'
        clause but still returns False for non-matching rows would pass. The load-bearing
        invariant is that admin B's active sessions survive the attempt.
        """
        admin = await _make_admin(make_user, async_db_session, "rev_ad_admin@example.com")
        other_admin = await _make_admin(make_user, async_db_session, "rev_ad_target@example.com")
        other_admin_token = create_access_token(str(other_admin.id))

        resp = await admin_client.post(
            f"/api/v1/admin/users/{other_admin.id}/revoke-sessions",
            headers=admin_headers(admin),
        )
        assert resp.status_code == 404

        # Confirm the targeted admin's token is still valid — the 404 above must be
        # purely a role-scope rejection, never a partial application of the revoke.
        resp = await admin_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {other_admin_token}"},
        )
        assert resp.status_code == 200
        await async_db_session.refresh(other_admin)
        assert other_admin.tokens_invalid_before is None

    async def test_revoke_nonexistent_user_returns_404(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        admin = await _make_admin(make_user, async_db_session, "rev_nf_admin@example.com")
        fake_id = uuid.uuid4()

        resp = await admin_client.post(
            f"/api/v1/admin/users/{fake_id}/revoke-sessions",
            headers=admin_headers(admin),
        )
        assert resp.status_code == 404

    async def test_revoke_requires_admin(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        """A regular user cannot call the revoke endpoint."""
        user, _ = await make_user(email="rev_nonadmin@example.com")
        target, _ = await make_user(email="rev_nonadmin_target@example.com")

        resp = await admin_client.post(
            f"/api/v1/admin/users/{target.id}/revoke-sessions",
            headers=user_headers(user),
        )
        assert resp.status_code == 403

    async def test_revoke_no_jwt_returns_401(self, admin_client: AsyncClient):
        fake_id = uuid.uuid4()
        resp = await admin_client.post(f"/api/v1/admin/users/{fake_id}/revoke-sessions")
        assert resp.status_code == 401


def _forge_token(
    sub: str,
    type_: str = "access",
    iat: datetime | None | object = "__auto__",
    exp: datetime | None = None,
) -> str:
    """Mint a JWT with arbitrary claims for negative-path coverage.

    Pass iat=None to omit the claim entirely; pass any other value (int, str, list,
    dict, float...) to land it in the payload unchanged — this is how we exercise
    the TypeError/OverflowError branches in access-token validation.
    """
    import jwt as _jwt

    from app.core.config import settings as _settings
    from app.core.security import ALGORITHM

    now = datetime.now(UTC)
    payload: dict = {
        "sub": sub,
        "exp": exp or (now + timedelta(minutes=15)),
        "type": type_,
    }
    if iat == "__auto__":
        payload["iat"] = now
    elif iat is not None:
        payload["iat"] = iat
    return _jwt.encode(payload, _settings.SECRET_KEY, algorithm=ALGORITHM)


class TestRevocationEdgeCases:
    """Edge-case coverage uncovered by the initial revocation test class.

    Pinned behaviours: legacy (no-iat) tokens after revocation; malformed iat shapes
    must 401 not 500; same-second post-revoke mints remain valid; revoke/suspend
    checks are ordered so revocation wins on access tokens, suspension wins on login.
    """

    async def test_missing_iat_with_revocation_set_is_rejected(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        """Legacy-token protection: a token without iat on a revoked user must fail.

        This guards the `token_iat is None or token_iat < cutoff` branch — removing
        the `None` part would silently re-admit pre-migration tokens post-revoke.
        """
        user, _ = await make_user(email="noeiat_revoked@example.com")
        user.tokens_invalid_before = datetime.now(UTC).replace(microsecond=0)
        async_db_session.add(user)
        await async_db_session.flush()

        token = _forge_token(str(user.id), iat=None)
        resp = await admin_client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Session has been revoked"

    async def test_missing_iat_without_revocation_is_accepted(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        """Inverse: no iat + no revocation set → token still works. Asymmetric handling
        of legacy tokens is intentional (we don't force re-login until admin decides to)."""
        user, _ = await make_user(email="noeiat_never_revoked@example.com")
        token = _forge_token(str(user.id), iat=None)

        resp = await admin_client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200

    @pytest.mark.parametrize(
        "bad_iat",
        [[1, 2], {"x": 1}, "not-a-number", 10**20],
        ids=["list", "dict", "string", "overflow"],
    )
    async def test_malformed_iat_returns_401_not_500(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
        bad_iat,
    ):
        """Every malformed iat shape must land on the 401 path — previously
        TypeError (from int() on a container), OverflowError (from fromtimestamp on
        1e20), and OSError (same, on some platforms) escaped the except clause and
        surfaced as a 500, handing attackers a crash oracle."""
        user, _ = await make_user(email=f"mal_iat_{abs(hash(str(bad_iat)))}@example.com")
        token = _forge_token(str(user.id), iat=bad_iat)

        resp = await admin_client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401

    async def test_same_second_post_revoke_mint_is_accepted(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        """Guards the `.replace(microsecond=0)` flooring in revoke_sessions.

        Scenario: revoke at 12:00:00.300; user immediately re-authenticates at
        12:00:00.800; the new access token's iat floors to 12:00:00. Without
        flooring the cutoff, 12:00:00 < 12:00:00.300 → fresh token rejected. With
        flooring, 12:00:00 < 12:00:00 is False → fresh token accepted (correct).
        """
        admin = await _make_admin(make_user, async_db_session, "ss_admin@example.com")
        user, _ = await make_user(email="ss_user@example.com")

        resp = await admin_client.post(
            f"/api/v1/admin/users/{user.id}/revoke-sessions",
            headers=admin_headers(admin),
        )
        assert resp.status_code == 200
        await async_db_session.refresh(user)
        cutoff = user.tokens_invalid_before
        assert cutoff is not None and cutoff.microsecond == 0

        # Mint a token with iat at exactly the cutoff second (same wall-clock second).
        same_second_token = _forge_token(str(user.id), iat=cutoff)
        resp = await admin_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {same_second_token}"},
        )
        assert resp.status_code == 200

    async def test_revoke_plus_suspend_precedence(
        self,
        admin_client: AsyncClient,
        async_db_session: AsyncSession,
        make_user,
    ):
        """The precedence is a UX contract: an old token hits revocation (401) before
        suspension (403), so the client's auth layer clears the cookie and sends the
        user to /login; at /login the suspension (403) surfaces the correct reason
        ('account suspended'). Swapping the order would leak 403 to stale tokens and
        break the cookie-clear path."""
        user, password = await make_user(email="rev_susp@example.com")
        old_token = _forge_token(str(user.id), iat=datetime.now(UTC) - timedelta(seconds=5))
        user.tokens_invalid_before = datetime.now(UTC).replace(microsecond=0)
        user.account_status = "suspended"
        async_db_session.add(user)
        await async_db_session.flush()

        # Revocation wins on the bearer path.
        resp = await admin_client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"}
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Session has been revoked"

        # Suspension wins on the login path (no token to revoke there).
        resp = await admin_client.post(
            "/api/v1/auth/login",
            json={"email": "rev_susp@example.com", "password": password},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Account is suspended"
