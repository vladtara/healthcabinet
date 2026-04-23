"""
Processing events — Redis pub/sub helpers for document status streaming.

Two Redis keys per document:
  doc:status:{document_id}  → pub/sub channel (worker publishes, SSE endpoint subscribes)
  doc:latest:{document_id}  → Redis STRING (latest event JSON, TTL=3600s, for late connectors)
"""

import json
import logging

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "doc:status:"
LATEST_KEY_PREFIX = "doc:latest:"
TERMINAL_STATUSES = {"completed", "failed", "partial"}
LATEST_EVENT_TTL = 3600  # seconds


async def publish_event(
    redis: object,
    document_id: str,
    event_type: str,
    progress: float,
    message: str,
) -> None:
    """Publish a document status event to Redis pub/sub and store as latest."""
    payload = json.dumps(
        {
            "event": event_type,
            "document_id": document_id,
            "progress": progress,
            "message": message,
        }
    )
    channel = f"{CHANNEL_PREFIX}{document_id}"
    latest_key = f"{LATEST_KEY_PREFIX}{document_id}"
    # Store latest first so a subscriber that connects immediately after can read it.
    await redis.set(latest_key, payload, ex=LATEST_EVENT_TTL)  # type: ignore[attr-defined]
    await redis.publish(channel, payload)  # type: ignore[attr-defined]


async def get_latest_event(redis: object, document_id: str) -> dict | None:  # type: ignore[type-arg]
    """Return the most recent event for a document, or None if not found."""
    latest_key = f"{LATEST_KEY_PREFIX}{document_id}"
    raw = await redis.get(latest_key)  # type: ignore[attr-defined]
    if raw is None:
        return None
    try:
        return json.loads(raw)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        logger.warning("events.corrupted_cached_payload", extra={"document_id": document_id})
        return None
