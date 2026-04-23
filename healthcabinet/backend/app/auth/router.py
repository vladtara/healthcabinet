import structlog
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service
from app.auth.dependencies import get_current_user
from app.auth.exceptions import AccountSuspendedError, DuplicateEmailError, InvalidCredentialsError
from app.auth.models import User
from app.auth.schemas import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import (
    check_login_rate_limit,
    check_refresh_rate_limit,
    check_register_rate_limit,
    reset_login_rate_limit,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["auth"])

# Shared cookie path — refresh token is scoped to the refresh endpoint only so it is
# NOT sent on every API request, reducing the attack surface. All three endpoints that
# set or clear this cookie must use the same path or the clearing cookie will be ignored.
_REFRESH_COOKIE_PATH = "/api/v1/auth/refresh"


def _refresh_cookie_clear_header() -> str:
    """Build the refresh-token clearing header for exception responses.

    FastAPI discards mutations made to the injected `Response` object once an
    `HTTPException` is raised, so the delete-cookie header must be attached to
    the exception itself.
    """
    cookie_response = Response()
    cookie_response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path=_REFRESH_COOKIE_PATH,
    )
    return cookie_response.headers["set-cookie"]


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    request: RegisterRequest,
    response: Response,
    req: Request,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    client_ip = req.client.host if req.client else None
    await check_register_rate_limit(ip=client_ip)
    try:
        user, access_token, refresh_token = await service.register_user(
            db,
            email=request.email,
            password=request.password,
            privacy_policy_version=request.privacy_policy_version,
        )
    except DuplicateEmailError:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists",
        ) from None

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=_REFRESH_COOKIE_PATH,
    )

    return RegisterResponse(
        id=user.id,
        email=user.email,
        access_token=access_token,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    response: Response,
    req: Request,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    # CSRF protection: reject requests with an Origin header that doesn't match an allowed
    # origin. Requests without Origin (curl, mobile apps, server-to-server) are permitted.
    origin = req.headers.get("origin")
    if origin and origin not in settings.ALLOWED_ORIGINS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin not allowed")
    client_ip = req.client.host if req.client else None
    if client_ip is None:
        logger.warning("auth.login.no_client_ip", detail="per-IP rate limiting skipped")
    await check_login_rate_limit(request.email, ip=client_ip)
    try:
        _user, access_token, refresh_token = await service.login_user(
            db, email=request.email, password=request.password
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except AccountSuspendedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended",
        ) from None

    # Reset per-email counter only on success. The per-IP counter is intentionally
    # NOT reset — resetting it would allow a valid account holder to bypass the IP
    # limit by interleaving successful logins with credential-stuffing attempts
    # against other accounts from the same IP.
    await reset_login_rate_limit(request.email, ip=None)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=_REFRESH_COOKIE_PATH,
    )
    return LoginResponse(access_token=access_token)


@router.post("/refresh", response_model=LoginResponse)
async def refresh(
    req: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    client_ip = req.client.host if req.client else None
    await check_refresh_rate_limit(ip=client_ip)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        access_token, new_refresh_token = await service.refresh_access_token(db, refresh_token)
    except AccountSuspendedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended",
            headers={"Set-Cookie": _refresh_cookie_clear_header()},
        ) from None
    except InvalidCredentialsError:
        # Clear invalid cookie to prevent retry loops.
        # This header must be attached to the exception because raised
        # HTTPExceptions bypass mutations on the injected response object.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing refresh token",
            headers={
                "WWW-Authenticate": "Bearer",
                "Set-Cookie": _refresh_cookie_clear_header(),
            },
        ) from None
    # Rotate the refresh token — the old cookie is superseded so a stolen cookie's
    # validity window is bounded to the time between two refresh operations.
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=_REFRESH_COOKIE_PATH,
    )
    return LoginResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    _current_user: User = Depends(get_current_user),
) -> None:
    # Requires a valid access token: defense-in-depth against force-logout via same-site
    # subdomain compromise. SameSite=Strict prevents cross-origin CSRF, but requiring auth
    # here means an attacker needs both the access token AND the ability to send it.
    # Accepted risk: no server-side refresh token blocklist is implemented.
    # A stolen refresh cookie remains valid for up to 30 days post-logout.
    # Mitigation: cookie is httpOnly + Secure + SameSite=Strict (XSS/CSRF resistant).
    # A blocklist (Redis-based token revocation) can be added in a future story if
    # the threat model for this health-data app requires it.
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path=_REFRESH_COOKIE_PATH,
    )


@router.get("/me", response_model=MeResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> MeResponse:
    """Return current authenticated user info. Used to verify get_current_user dependency."""
    return MeResponse(
        id=str(current_user.id),
        email=current_user.email,
        role=current_user.role,
        tier=current_user.tier,
    )
