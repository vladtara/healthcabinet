"""Unit tests for worker-side MinIO object reads."""

from unittest.mock import MagicMock, patch

import pytest

from app.documents.storage import get_object_bytes


def _make_body(payload: bytes) -> MagicMock:
    body = MagicMock()
    body.read.return_value = payload
    body.close = MagicMock()
    return body


def test_get_object_bytes_reads_payload_within_limit():
    body = _make_body(b"abc")
    s3_client = MagicMock()
    s3_client.get_object.return_value = {"Body": body, "ContentLength": 3}

    with patch("app.documents.storage.settings.DOCUMENT_PROCESSING_MAX_BYTES", 5):
        payload = get_object_bytes(s3_client, "bucket", "key")

    assert payload == b"abc"
    body.close.assert_called_once()


def test_get_object_bytes_rejects_oversized_content_length():
    body = _make_body(b"abc")
    s3_client = MagicMock()
    s3_client.get_object.return_value = {"Body": body, "ContentLength": 10}

    with (
        patch("app.documents.storage.settings.DOCUMENT_PROCESSING_MAX_BYTES", 5),
        pytest.raises(ValueError, match="size limit"),
    ):
        get_object_bytes(s3_client, "bucket", "key")

    body.close.assert_called_once()


def test_get_object_bytes_rejects_payload_exceeding_stream_limit():
    body = _make_body(b"abcdef")
    s3_client = MagicMock()
    s3_client.get_object.return_value = {"Body": body}

    with (
        patch("app.documents.storage.settings.DOCUMENT_PROCESSING_MAX_BYTES", 5),
        pytest.raises(ValueError, match="size limit"),
    ):
        get_object_bytes(s3_client, "bucket", "key")

    body.read.assert_called_once_with(6)
    body.close.assert_called_once()
