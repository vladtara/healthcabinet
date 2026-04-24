"""Unit tests for the Claude extraction boundary."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.processing.extractor import extract_from_document


@pytest.mark.asyncio
async def test_extract_from_document_validates_structured_output():
    response_payload = {
        "measured_at": "2026-03-23T00:00:00Z",
        "source_language": "en",
        "raw_lab_name": "Health Lab",
        "values": [
            {
                "biomarker_name": "Glucose",
                "value": 95.0,
                "unit": "mg/dL",
                "reference_range_low": 70.0,
                "reference_range_high": 99.0,
                "confidence": 0.92,
            }
        ],
    }
    fake_client = SimpleNamespace(
        messages=SimpleNamespace(
            create=AsyncMock(
                return_value=SimpleNamespace(
                    content=[SimpleNamespace(text=json.dumps(response_payload))]
                )
            )
        )
    )

    with patch("app.processing.extractor._get_client", return_value=fake_client):
        result = await extract_from_document(
            document_id="doc-1",
            document_bytes=b"%PDF-1.4",
            mime_type="application/pdf",
        )

    assert result.raw_lab_name == "Health Lab"
    assert result.values[0].confidence == 0.92


@pytest.mark.asyncio
async def test_extract_from_document_does_not_send_unsupported_metadata():
    fake_create = AsyncMock(
        return_value=SimpleNamespace(
            content=[
                SimpleNamespace(
                    text='{"measured_at": null, "source_language": null, "raw_lab_name": null, "values": []}'
                )
            ]
        )
    )
    fake_client = SimpleNamespace(messages=SimpleNamespace(create=fake_create))

    with patch("app.processing.extractor._get_client", return_value=fake_client):
        await extract_from_document(
            document_id="doc-request-shape",
            document_bytes=b"%PDF-1.4",
            mime_type="application/pdf",
        )

    kwargs = fake_create.await_args.kwargs
    assert "metadata" not in kwargs
    assert kwargs["model"]
    assert kwargs["messages"]
    assert kwargs["system"]


@pytest.mark.asyncio
async def test_extract_from_document_accepts_provider_structured_output():
    response_payload = {
        "measured_at": "2026-03-23T00:00:00Z",
        "source_language": "en",
        "raw_lab_name": "Structured Lab",
        "values": [],
    }
    fake_client = SimpleNamespace(
        messages=SimpleNamespace(
            create=AsyncMock(return_value=SimpleNamespace(output=response_payload, content=[]))
        )
    )

    with patch("app.processing.extractor._get_client", return_value=fake_client):
        result = await extract_from_document(
            document_id="doc-structured",
            document_bytes=b"%PDF-1.4",
            mime_type="application/pdf",
        )

    assert result.raw_lab_name == "Structured Lab"


@pytest.mark.asyncio
async def test_extract_from_document_rejects_trailing_non_json_content():
    fake_client = SimpleNamespace(
        messages=SimpleNamespace(
            create=AsyncMock(
                return_value=SimpleNamespace(
                    content=[
                        SimpleNamespace(
                            text='{"measured_at": null, "source_language": null, "raw_lab_name": null, "values": []}\nextra'
                        )
                    ]
                )
            )
        )
    )

    with (
        patch("app.processing.extractor._get_client", return_value=fake_client),
        pytest.raises(ValueError, match="trailing non-JSON content"),
    ):
        await extract_from_document(
            document_id="doc-bad-json",
            document_bytes=b"%PDF-1.4",
            mime_type="application/pdf",
        )


@pytest.mark.asyncio
async def test_extract_from_document_handles_markdown_fenced_json():
    response_payload = {
        "measured_at": "2026-03-26T10:38:00",
        "source_language": "Ukrainian",
        "raw_lab_name": "Test Lab",
        "values": [
            {
                "biomarker_name": "Hemoglobin",
                "value": 13.5,
                "unit": "g/dL",
                "reference_range_low": 12.0,
                "reference_range_high": 16.0,
                "confidence": 0.95,
            }
        ],
    }
    import json as _json

    fenced_text = f"```json\n{_json.dumps(response_payload)}\n```"
    fake_client = SimpleNamespace(
        messages=SimpleNamespace(
            create=AsyncMock(
                return_value=SimpleNamespace(content=[SimpleNamespace(text=fenced_text)])
            )
        )
    )

    with patch("app.processing.extractor._get_client", return_value=fake_client):
        result = await extract_from_document(
            document_id="doc-fenced",
            document_bytes=b"%PDF-1.4",
            mime_type="application/pdf",
        )

    assert result.raw_lab_name == "Test Lab"
    assert result.values[0].biomarker_name == "Hemoglobin"
    assert result.values[0].confidence == 0.95


@pytest.mark.asyncio
async def test_extract_from_document_raises_on_truncated_response():
    fake_client = SimpleNamespace(
        messages=SimpleNamespace(
            create=AsyncMock(
                return_value=SimpleNamespace(
                    stop_reason="max_tokens",
                    content=[SimpleNamespace(text='{"measured_at": null, "values": [{"biomar')],
                )
            )
        )
    )

    with (
        patch("app.processing.extractor._get_client", return_value=fake_client),
        pytest.raises(ValueError, match="truncated"),
    ):
        await extract_from_document(
            document_id="doc-truncated",
            document_bytes=b"%PDF-1.4",
            mime_type="application/pdf",
        )


@pytest.mark.asyncio
async def test_extract_from_document_rejects_unsupported_mime_type():
    with pytest.raises(ValueError, match="Unsupported document MIME type"):
        await extract_from_document(
            document_id="doc-2",
            document_bytes=b"text",
            mime_type="text/plain",
        )
