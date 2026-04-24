"""
Processing router — SSE endpoint for real-time document status streaming.

Auth: Supports dual authentication for zero-downtime migration:
  1. Authorization: Bearer <token> header (preferred — used by fetch-based SSE clients)
  2. ?token= query parameter (legacy — used by EventSource clients, to be removed post-migration)
The backend validates both identically via verify_access_token().
"""

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import suppress
from typing import cast

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import resolve_access_token
from app.core.config import settings
from app.documents.repository import get_document_by_id
from app.processing.dependencies import get_db
from app.processing.events import (
    CHANNEL_PREFIX,
    TERMINAL_STATUSES,
    get_latest_event,
)
from app.processing.schemas import STAGE_MESSAGES

router = APIRouter(tags=["processing"])
logger = logging.getLogger(__name__)

# Maximum stream duration matches ingress proxy-read-timeout (120s)
_MAX_STREAM_SECONDS = 120
_HEARTBEAT_INTERVAL_SECONDS = 5


def _sse_frame(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _heartbeat_frame() -> str:
    return ":\n\n"


def _redis_from_url() -> aioredis.Redis:
    return cast(Callable[..., aioredis.Redis], aioredis.from_url)(
        settings.REDIS_URL,
        decode_responses=True,
    )


@router.get("/documents/{document_id}/status")
async def document_status_stream(
    document_id: uuid.UUID,
    token: str | None = Query(
        default=None,
        description="Access JWT (legacy EventSource path — prefer Authorization header)",
    ),
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """SSE stream of document processing status events.

    Auth: accepts Authorization: Bearer <token> header (preferred) or ?token= query
    parameter (legacy). Header takes precedence when both are present.

    Emits events in sequence:
      upload_started → reading → extracting → generating → completed | failed | partial

    For already-completed documents, emits the terminal event immediately and closes.
    """
    # 1. Resolve user from header (preferred) or query param (legacy fallback).
    # resolve_access_token applies the full access-token validation pipeline —
    # signature, type, revocation (users.tokens_invalid_before), and account
    # suspension — so this endpoint cannot be used with a revoked or suspended
    # session even when the caller authenticates via the EventSource ?token= path.
    raw_token: str | None = None
    if authorization is not None:
        scheme, _, credentials = authorization.strip().partition(" ")
        if scheme.lower() != "bearer" or not credentials.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raw_token = credentials.strip()
    elif token:
        raw_token = token
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    current_user = await resolve_access_token(raw_token, db)
    user_id = current_user.id

    # 2. Verify document ownership (raises HTTP 404 if not found or wrong user)
    doc = await get_document_by_id(db, document_id, user_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        # Fast-path: document already in terminal state
        if doc.status in TERMINAL_STATUSES:
            event_type = f"document.{doc.status}"
            msg, progress = STAGE_MESSAGES.get(event_type, (f"Document {doc.status}", 1.0))
            yield _sse_frame(
                {
                    "event": event_type,
                    "document_id": str(document_id),
                    "progress": progress,
                    "message": msg,
                }
            )
            return

        # Create a dedicated Redis connection for pub/sub subscription.
        # A subscribed connection cannot execute other commands — it is locked
        # in subscribe mode, so we must NOT reuse get_redis() here.
        pubsub_redis = _redis_from_url()
        pubsub = pubsub_redis.pubsub()
        check_redis = None
        try:
            channel = f"{CHANNEL_PREFIX}{document_id}"

            # Subscribe FIRST, then check latest — order prevents race where an event
            # is published between the check and the subscribe.
            await pubsub.subscribe(channel)

            # Check for a cached event that was published before we connected.
            # Use a separate (non-pubsub) connection since pubsub is locked.
            check_redis = _redis_from_url()
            try:
                latest = await get_latest_event(check_redis, str(document_id))
            finally:
                await check_redis.aclose()
                check_redis = None

            last_sent_payload: str | None = None

            if latest is not None:
                last_sent_payload = json.dumps(latest)
                yield _sse_frame(latest)
                if latest.get("event", "").split(".")[-1] in TERMINAL_STATUSES:
                    return

            loop = asyncio.get_running_loop()
            deadline = loop.time() + _MAX_STREAM_SECONDS
            while loop.time() < deadline:
                remaining = deadline - loop.time()
                timeout = min(_HEARTBEAT_INTERVAL_SECONDS, remaining)
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=timeout)
                if message is None:
                    if loop.time() < deadline:
                        yield _heartbeat_frame()
                    continue
                if message["type"] != "message":
                    continue
                data = message["data"]
                if not isinstance(data, str) or data == last_sent_payload:
                    continue
                last_sent_payload = data
                yield f"data: {data}\n\n"

                try:
                    event_data = json.loads(data)
                    event_name = event_data.get("event", "")
                    status_part = event_name.split(".")[-1] if "." in event_name else ""
                    if status_part in TERMINAL_STATUSES:
                        return
                except (json.JSONDecodeError, AttributeError):
                    continue
        except asyncio.CancelledError:
            raise
        except RedisError:
            logger.warning("sse.redis_error", extra={"document_id": str(document_id)})
            msg, progress = STAGE_MESSAGES.get("document.failed", ("Processing failed", 0.0))
            yield _sse_frame(
                {
                    "event": "document.failed",
                    "document_id": str(document_id),
                    "progress": progress,
                    "message": msg,
                }
            )
        finally:
            close_pubsub = cast(Callable[[], Awaitable[None]], pubsub.aclose)
            close_pubsub_redis = cast(Callable[[], Awaitable[None]], pubsub_redis.aclose)
            coroutines = [pubsub.unsubscribe(), close_pubsub(), close_pubsub_redis()]
            if check_redis is not None:
                close_check_redis = cast(Callable[[], Awaitable[None]], check_redis.aclose)
                coroutines.append(close_check_redis())
            for coro in coroutines:
                with suppress(Exception):
                    await coro

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
