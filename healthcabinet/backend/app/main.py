from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Any

import sentry_sdk
import structlog
from arq import create_pool as arq_create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.auth.service import ensure_bootstrap_admin, init_dummy_hash
from app.core.config import settings
from app.core.database import AsyncSessionLocal, import_orm_models
from app.core.middleware import RequestIDMiddleware, configure_logging

configure_logging()
import_orm_models()
logger = structlog.get_logger()

if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Pre-compute bcrypt dummy hash to avoid blocking the event loop on first login
    await init_dummy_hash()
    if settings.BOOTSTRAP_ADMIN_EMAIL and settings.BOOTSTRAP_ADMIN_PASSWORD:
        async with AsyncSessionLocal() as session:
            await ensure_bootstrap_admin(
                session,
                email=str(settings.BOOTSTRAP_ADMIN_EMAIL),
                password=settings.BOOTSTRAP_ADMIN_PASSWORD,
                privacy_policy_version=settings.PRIVACY_POLICY_VERSION,
            )
    if settings.ENVIRONMENT == "production" and settings.TRUSTED_PROXY_IPS == "*":
        logger.warning(
            "security.trusted_proxy_wildcard",
            detail=(
                "TRUSTED_PROXY_IPS is '*' in production. Clients can forge X-Forwarded-For "
                "headers, bypassing per-IP rate limiting. Set TRUSTED_PROXY_IPS to your "
                "load balancer's IP or VPC CIDR to prevent this."
            ),
        )
    # ARQ Redis pool for background job enqueueing (document processing pipeline)
    try:
        app.state.arq_redis = await arq_create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    except Exception:
        logger.warning("arq.pool_unavailable", detail="ARQ Redis pool could not be created")
        app.state.arq_redis = None
    yield
    if app.state.arq_redis is not None:
        await app.state.arq_redis.close()


app = FastAPI(
    title="HealthCabinet API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
)

# CORS — configure allowed origins via ALLOWED_ORIGINS in settings/.env
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestIDMiddleware)

# ProxyHeadersMiddleware: populate request.client.host from X-Forwarded-For so that
# IP-based rate limiting reflects the real client IP in production (not the proxy's IP).
# trusted_hosts is configured via TRUSTED_PROXY_IPS — set to your load balancer's IP or
# VPC CIDR in production to prevent clients from forging X-Forwarded-For headers.
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=settings.TRUSTED_PROXY_IPS)


# RFC 7807 HTTPException handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    from http import HTTPStatus

    try:
        title = HTTPStatus(exc.status_code).phrase
    except ValueError:
        title = "Error"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": "about:blank",
            "title": title,
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": str(request.url),
        },
        # Preserve custom headers (e.g. Retry-After on 429, WWW-Authenticate on 401)
        headers=dict(exc.headers) if exc.headers else None,
    )


def _serialize_validation_errors(errors: Sequence[Any]) -> list[dict[str, Any]]:
    """Make Pydantic validation errors JSON-serializable by converting non-primitive ctx values."""
    result = []
    for error in errors:
        err = dict(error)
        if "ctx" in err and isinstance(err["ctx"], dict):
            err["ctx"] = {
                k: str(v)
                if not isinstance(v, (str, int, float, bool, list, dict, type(None)))
                else v
                for k, v in err["ctx"].items()
            }
        result.append(err)
    return result


# RFC 7807 RequestValidationError handler (Pydantic 422 errors)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "type": "about:blank",
            "title": "Unprocessable Entity",
            "status": 422,
            "detail": _serialize_validation_errors(exc.errors()),
            "instance": str(request.url),
        },
    )


# RFC 7807 global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", exc_info=exc, path=request.url.path)
    headers = None
    request_id = request.scope.get("request_id")
    if isinstance(request_id, str):
        headers = {"X-Request-ID": request_id}
    return JSONResponse(
        status_code=500,
        content={
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": str(exc) if settings.ENVIRONMENT == "development" else "An error occurred",
            "instance": str(request.url),
        },
        headers=headers,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Domain router imports are placed AFTER app instantiation to avoid circular imports
# (routers import from app.core which imports settings, and settings is used above).
# When adding new domain routers, follow this same pattern:
#   from app.<domain>.router import router as <domain>_router  # noqa: E402
#   app.include_router(<domain>_router, prefix="/api/v1")
from app.admin.router import router as admin_router  # noqa: E402
from app.ai.router import router as ai_router  # noqa: E402
from app.auth.router import router as auth_router  # noqa: E402
from app.documents.exceptions import (  # noqa: E402
    DocumentNotFoundError,
    DocumentRetryNotAllowedError,
    DocumentYearConfirmationInvalidError,
    DocumentYearConfirmationNotAllowedError,
    UploadLimitExceededError,
)
from app.documents.router import router as documents_router  # noqa: E402
from app.health_data.exceptions import HealthValueNotFoundError  # noqa: E402
from app.health_data.router import router as health_data_router  # noqa: E402
from app.processing.exceptions import ProcessingError  # noqa: E402
from app.processing.router import router as processing_router  # noqa: E402
from app.users.router import router as users_router  # noqa: E402


@app.exception_handler(DocumentNotFoundError)
async def document_not_found_handler(request: Request, exc: DocumentNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "type": "about:blank",
            "title": "Not Found",
            "status": 404,
            "detail": exc.detail,
            "instance": str(request.url.path),
        },
    )


@app.exception_handler(HealthValueNotFoundError)
async def health_value_not_found_handler(
    request: Request, exc: HealthValueNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "type": "about:blank",
            "title": "Not Found",
            "status": 404,
            "detail": exc.detail,
            "instance": str(request.url.path),
        },
    )


@app.exception_handler(ProcessingError)
async def processing_error_handler(request: Request, exc: ProcessingError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "type": "about:blank",
            "title": "Processing Error",
            "status": 422,
            "detail": exc.detail,
            "instance": str(request.url.path),
        },
    )


@app.exception_handler(DocumentRetryNotAllowedError)
async def document_retry_not_allowed_handler(
    request: Request, exc: DocumentRetryNotAllowedError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "type": "about:blank",
            "title": "Conflict",
            "status": 409,
            "detail": exc.detail,
            "instance": str(request.url.path),
        },
    )


@app.exception_handler(DocumentYearConfirmationNotAllowedError)
async def document_year_confirmation_not_allowed_handler(
    request: Request, exc: DocumentYearConfirmationNotAllowedError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "type": "about:blank",
            "title": "Conflict",
            "status": 409,
            "detail": exc.detail,
            "instance": str(request.url.path),
        },
    )


@app.exception_handler(DocumentYearConfirmationInvalidError)
async def document_year_confirmation_invalid_handler(
    request: Request, exc: DocumentYearConfirmationInvalidError
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "type": "about:blank",
            "title": "Bad Request",
            "status": 400,
            "detail": exc.detail,
            "instance": str(request.url.path),
        },
    )


@app.exception_handler(UploadLimitExceededError)
async def upload_limit_handler(request: Request, exc: UploadLimitExceededError) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "type": "about:blank",
            "title": "Too Many Requests",
            "status": 429,
            "detail": exc.detail,
            "instance": str(request.url.path),
        },
        headers={"Retry-After": "86400"},
    )


app.include_router(admin_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(health_data_router, prefix="/api/v1")
app.include_router(processing_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
