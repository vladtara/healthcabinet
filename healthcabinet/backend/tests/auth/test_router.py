import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.users.models import ConsentLog


async def test_register_success(test_client: AsyncClient, async_db_session: AsyncSession):
    payload = {
        "email": "new@example.com",
        "password": "securepassword",
        "gdpr_consent": True,
        "privacy_policy_version": "1.0",
    }
    response = await test_client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["email"] == "new@example.com"

    user_id = uuid.UUID(data["id"])

    # Verify user record in DB
    user_result = await async_db_session.execute(select(User).where(User.id == user_id))
    assert user_result.scalar_one_or_none() is not None

    # Verify consent log was created for this specific user
    consent_result = await async_db_session.execute(
        select(ConsentLog).where(ConsentLog.user_id == user_id)
    )
    consent_log = consent_result.scalar_one_or_none()
    assert consent_log is not None
    assert consent_log.consent_type == "health_data_processing"
    assert consent_log.privacy_policy_version == "1.0"

    # Verify refresh_token cookie was set with required security attributes
    assert "refresh_token" in response.cookies
    set_cookie = response.headers.get("set-cookie", "").lower()
    assert "httponly" in set_cookie
    assert "secure" in set_cookie
    assert "samesite=strict" in set_cookie
    assert "path=/api/v1/auth/refresh" in set_cookie


async def test_register_duplicate_email(test_client: AsyncClient, make_user):
    await make_user(email="dupe@example.com")

    payload = {
        "email": "dupe@example.com",
        "password": "securepassword",
        "gdpr_consent": True,
        "privacy_policy_version": "1.0",
    }
    response = await test_client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 409
    data = response.json()
    # Full RFC 7807 shape
    assert data["type"] == "about:blank"
    assert data["title"] == "Conflict"
    assert data["status"] == 409
    assert data["detail"] == "An account with this email already exists"
    assert "instance" in data


async def test_register_gdpr_consent_required(test_client: AsyncClient):
    payload = {
        "email": "gdpr@example.com",
        "password": "securepassword",
        "gdpr_consent": False,
        "privacy_policy_version": "1.0",
    }
    response = await test_client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert data["type"] == "about:blank"
    assert data["title"] == "Unprocessable Entity"
    assert data["status"] == 422
    assert "detail" in data
    assert "instance" in data


async def test_register_password_too_short(test_client: AsyncClient):
    payload = {
        "email": "short@example.com",
        "password": "short",
        "gdpr_consent": True,
        "privacy_policy_version": "1.0",
    }
    response = await test_client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert data["type"] == "about:blank"
    assert data["title"] == "Unprocessable Entity"
    assert data["status"] == 422
    assert "detail" in data
    assert "instance" in data


async def test_register_password_too_long(test_client: AsyncClient):
    # bcrypt silently truncates at 72 bytes; max_length=72 prevents silent truncation
    payload = {
        "email": "toolong@example.com",
        "password": "a" * 73,
        "gdpr_consent": True,
        "privacy_policy_version": "1.0",
    }
    response = await test_client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert data["type"] == "about:blank"
    assert data["title"] == "Unprocessable Entity"
    assert data["status"] == 422
    assert "detail" in data
    assert "instance" in data


async def test_register_password_too_long_utf8(test_client: AsyncClient):
    # "あ" is 3 bytes in UTF-8; 25 chars × 3 bytes = 75 bytes > 72 byte bcrypt limit
    # but only 25 Unicode characters — exercises byte-vs-character distinction
    payload = {
        "email": "utf8toolong@example.com",
        "password": "あ" * 25,
        "gdpr_consent": True,
        "privacy_policy_version": "1.0",
    }
    response = await test_client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert data["type"] == "about:blank"
    assert data["title"] == "Unprocessable Entity"
    assert data["status"] == 422
    assert "detail" in data
    assert "instance" in data


async def test_register_empty_privacy_policy_version(test_client: AsyncClient):
    payload = {
        "email": "ppv@example.com",
        "password": "securepassword",
        "gdpr_consent": True,
        "privacy_policy_version": "",
    }
    response = await test_client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert data["type"] == "about:blank"
    assert data["title"] == "Unprocessable Entity"
    assert data["status"] == 422
    assert "detail" in data
    assert "instance" in data


# ── Login / Refresh / Logout tests ──────────────────────────────────────────


async def test_login_success(test_client: AsyncClient, make_user):
    user, password = await make_user(email="login@example.com")
    response = await test_client.post(
        "/api/v1/auth/login", json={"email": "login@example.com", "password": password}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "refresh_token" in response.cookies

    # Verify refresh cookie security attributes — regression guard for cookie misconfiguration
    set_cookie = response.headers.get("set-cookie", "").lower()
    assert "httponly" in set_cookie
    assert "secure" in set_cookie
    assert "samesite=strict" in set_cookie
    assert "path=/api/v1/auth/refresh" in set_cookie


async def test_login_wrong_password(test_client: AsyncClient, make_user):
    await make_user(email="wrongpw@example.com")
    response = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@example.com", "password": "definitelywrong"},
    )

    assert response.status_code == 401
    data = response.json()
    assert data["type"] == "about:blank"
    assert data["title"] == "Unauthorized"
    assert data["status"] == 401
    assert data["detail"] == "Invalid email or password"
    assert "instance" in data


async def test_login_nonexistent_email(test_client: AsyncClient):
    # Same 401 as wrong password — no user enumeration
    response = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "somepassword"},
    )

    assert response.status_code == 401
    data = response.json()
    assert data["type"] == "about:blank"
    assert data["title"] == "Unauthorized"
    assert data["status"] == 401
    assert data["detail"] == "Invalid email or password"
    assert "instance" in data


async def test_refresh_token_success(test_client: AsyncClient, make_user):
    user, password = await make_user(email="refresh@example.com")
    login_resp = await test_client.post(
        "/api/v1/auth/login", json={"email": "refresh@example.com", "password": password}
    )
    assert login_resp.status_code == 200
    # Extract the refresh token from Set-Cookie and pass it explicitly
    # (httpx with ASGITransport doesn't auto-send secure cookies)
    refresh_token_value = login_resp.cookies.get("refresh_token")
    assert refresh_token_value is not None, "refresh_token cookie must be set on login"

    refresh_resp = await test_client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": refresh_token_value},
    )

    assert refresh_resp.status_code == 200
    data = refresh_resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_refresh_token_missing_cookie(test_client: AsyncClient):
    response = await test_client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == 401
    assert "refresh" in data["detail"].lower()


async def test_logout_clears_cookie(test_client: AsyncClient, make_user):
    user, password = await make_user(email="logout@example.com")
    login_resp = await test_client.post(
        "/api/v1/auth/login", json={"email": "logout@example.com", "password": password}
    )
    access_token = login_resp.json()["access_token"]
    refresh_token_value = login_resp.cookies.get("refresh_token")
    assert refresh_token_value is not None

    # Send the refresh cookie in the logout request — simulates the browser sending
    # the httpOnly cookie to the logout endpoint (browser does this automatically).
    # Without this, the test verifies clearing-header-on-any-request rather than
    # clearing-the-cookie-that-was-actually-set-on-login.
    response = await test_client.post(
        "/api/v1/auth/logout",
        cookies={"refresh_token": refresh_token_value},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 204
    # After logout the refresh_token cookie should be cleared with max-age=0 and
    # security attributes preserved — a regression removing secure/httponly on the
    # clearing cookie would allow a non-HTTPS replacement to be set.
    set_cookie = response.headers.get("set-cookie", "").lower()
    assert "max-age=0" in set_cookie
    assert "httponly" in set_cookie
    assert "secure" in set_cookie
    assert "samesite=strict" in set_cookie

    # Verify that a post-logout refresh attempt (no cookie) returns 401 — simulates
    # the browser state after the clearing Set-Cookie expires the cookie.
    # NOTE: Server-side token revocation is an accepted risk (no blocklist); the old
    # JWT remains valid for its remaining 30-day TTL. This test verifies the cookie
    # is cleared so the browser cannot auto-refresh the session.
    refresh_resp = await test_client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 401


async def test_get_current_user_valid_token(test_client: AsyncClient, make_user):
    user, password = await make_user(email="authme@example.com")
    login_resp = await test_client.post(
        "/api/v1/auth/login", json={"email": "authme@example.com", "password": password}
    )
    access_token = login_resp.json()["access_token"]

    response = await test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "authme@example.com"


async def test_get_current_user_no_token(test_client: AsyncClient):
    response = await test_client.get("/api/v1/auth/me")
    # Without Bearer token: 401 (HTTPBearer returns 401 when no credentials provided)
    assert response.status_code == 401


async def test_get_current_user_expired_token(test_client: AsyncClient):
    from datetime import UTC, datetime, timedelta

    import jwt

    from app.core.config import settings
    from app.core.security import ALGORITHM

    expired_payload = {
        "sub": "00000000-0000-0000-0000-000000000000",
        "type": "access",
        "exp": datetime.now(UTC) - timedelta(minutes=1),
    }
    expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    response = await test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


async def test_get_current_user_with_refresh_token(test_client: AsyncClient, make_user):
    """Verify get_current_user rejects a refresh JWT presented as a Bearer access token.

    get_current_user checks payload["type"] == "access" and raises 401 when it sees
    "refresh". This test provides regression protection for that check — without it,
    a refactor removing the type check would silently allow refresh tokens as auth.
    """
    user, password = await make_user(email="refreshasbearer@example.com")
    login_resp = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "refreshasbearer@example.com", "password": password},
    )
    assert login_resp.status_code == 200
    refresh_token_value = login_resp.cookies.get("refresh_token")
    assert refresh_token_value is not None, "refresh_token cookie must be set on login"

    # Use the refresh token as a Bearer token — must be rejected with 401
    response = await test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token_value}"},
    )
    assert response.status_code == 401


async def test_login_rate_limit_retry_after_header(test_client: AsyncClient):
    """Verify the RFC 7807 exception handler forwards custom headers to the HTTP response.

    The handler previously stripped all custom HTTPException headers, causing Retry-After
    (429) and WWW-Authenticate (401) to be invisible to clients. This test mocks the rate
    limiter to raise a 429 with Retry-After and asserts the header survives to the client.
    """
    from unittest.mock import AsyncMock, patch

    from fastapi import HTTPException

    with patch(
        "app.auth.router.check_login_rate_limit",
        new_callable=AsyncMock,
        side_effect=HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again in 60 seconds.",
            headers={"Retry-After": "60"},
        ),
    ):
        response = await test_client.post(
            "/api/v1/auth/login",
            json={"email": "rate@example.com", "password": "password123"},
        )

    assert response.status_code == 429
    assert response.headers.get("retry-after") == "60"
