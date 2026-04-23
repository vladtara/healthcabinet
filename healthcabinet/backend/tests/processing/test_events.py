"""Unit tests for processing/events.py."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.processing.events import (
    CHANNEL_PREFIX,
    LATEST_EVENT_TTL,
    LATEST_KEY_PREFIX,
    get_latest_event,
    publish_event,
)


@pytest.mark.asyncio
async def test_publish_stores_latest_event():
    """publish_event stores the event as the latest key with correct TTL."""
    redis = MagicMock()
    redis.set = AsyncMock()
    redis.publish = AsyncMock()

    await publish_event(redis, "doc-123", "document.reading", 0.25, "Reading document…")

    expected_payload = json.dumps(
        {
            "event": "document.reading",
            "document_id": "doc-123",
            "progress": 0.25,
            "message": "Reading document…",
        }
    )
    redis.set.assert_called_once_with(
        f"{LATEST_KEY_PREFIX}doc-123", expected_payload, ex=LATEST_EVENT_TTL
    )
    redis.publish.assert_called_once_with(f"{CHANNEL_PREFIX}doc-123", expected_payload)


@pytest.mark.asyncio
async def test_get_latest_event_returns_none_when_missing():
    """get_latest_event returns None when no cached event exists."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)

    result = await get_latest_event(redis, "doc-456")

    assert result is None
    redis.get.assert_called_once_with(f"{LATEST_KEY_PREFIX}doc-456")


@pytest.mark.asyncio
async def test_get_latest_event_returns_parsed_dict():
    """get_latest_event returns parsed dict when cached event exists."""
    event_data = {
        "event": "document.completed",
        "document_id": "doc-789",
        "progress": 1.0,
        "message": "Processing complete",
    }
    redis = MagicMock()
    redis.get = AsyncMock(return_value=json.dumps(event_data))

    result = await get_latest_event(redis, "doc-789")

    assert result == event_data


@pytest.mark.asyncio
async def test_get_latest_event_handles_corrupted_json():
    """Corrupted cached event payloads are ignored instead of crashing the stream."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value="{not-json")

    result = await get_latest_event(redis, "doc-corrupt")

    assert result is None
