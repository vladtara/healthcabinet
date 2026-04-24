"""Build a ZIP archive containing all user data for GDPR data export."""

import csv
import io
import re
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import PurePosixPath

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.users.export_repository import (
    get_document_file_bytes,
    list_admin_corrections_for_export,
    list_ai_interpretations_for_export,
    list_consent_logs_for_export,
    list_documents_for_export,
    list_health_values_for_export,
)

logger = structlog.get_logger()


def _sanitize_text(value: object | None) -> str:
    if value is None:
        return ""
    return str(value).encode("utf-8", errors="replace").decode("utf-8")


def _csv_bytes(headers: list[str], rows: list[list[str]]) -> bytes:
    """Write CSV data to a UTF-8 byte string."""
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\n")
    writer.writerow([_sanitize_text(header) for header in headers])
    writer.writerows([[_sanitize_text(cell) for cell in row] for row in rows])
    return buf.getvalue().encode("utf-8", errors="replace")


def _build_summary(
    user: User,
    *,
    doc_count: int,
    skipped_documents: int,
    hv_count: int,
    ai_count: int,
    skipped_health_values: int,
    skipped_ai_interpretations: int,
) -> str:
    lines = [
        "HealthCabinet Data Export",
        "=========================",
        f"Email: {_sanitize_text(user.email)}",
        f"Account created: {_sanitize_text(user.created_at)}",
        f"Account status: {_sanitize_text(user.account_status)}",
        f"Last login: {_sanitize_text(user.last_login_at or 'Never')}",
        f"Export generated: {_sanitize_text(datetime.now(UTC))}",
        f"Documents: {doc_count}",
        f"Health values: {hv_count}",
        f"AI interpretations: {ai_count}",
    ]
    if skipped_documents:
        lines.append(f"Documents unavailable due to retrieval errors: {skipped_documents}")
    if skipped_health_values:
        lines.append(f"Health values unavailable due to decryption errors: {skipped_health_values}")
    if skipped_ai_interpretations:
        lines.append(
            f"AI interpretations unavailable due to decryption errors: {skipped_ai_interpretations}"
        )
    return "\n".join(lines) + "\n"


def _document_entry_name(filename: str, seen_names: set[str]) -> str:
    normalized = filename.replace("\\", "/")
    candidate = PurePosixPath(normalized).name.strip()
    candidate = re.sub(r"[\x00-\x1f\x7f]+", "_", candidate)
    if candidate in {"", ".", ".."}:
        candidate = "document"

    base_path = PurePosixPath(candidate)
    suffix = base_path.suffix
    stem = base_path.stem if suffix else candidate
    resolved = candidate
    counter = 1
    while resolved in seen_names:
        resolved = f"{stem}-{counter}{suffix}"
        counter += 1
    seen_names.add(resolved)
    return f"documents/{resolved}"


async def build_export_zip(
    db: AsyncSession,
    user: User,
    s3_client: object,
    bucket: str,
) -> io.BytesIO:
    """Collect all user data and package into an in-memory ZIP archive."""
    user_id: uuid.UUID = user.id

    # Collect all data
    documents = await list_documents_for_export(db, user_id)
    hv_result = await list_health_values_for_export(db, user_id)
    ai_result = await list_ai_interpretations_for_export(db, user_id)
    consent_logs = await list_consent_logs_for_export(db, user_id)
    admin_corrections = await list_admin_corrections_for_export(db, user_id)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Documents
        exported_doc_count = 0
        skipped_document_count = 0
        seen_document_names: set[str] = set()
        for doc in documents:
            file_bytes = await get_document_file_bytes(db, user_id, doc, s3_client, bucket)
            if file_bytes is not None:
                zf.writestr(_document_entry_name(doc.filename, seen_document_names), file_bytes)
                exported_doc_count += 1
            else:
                skipped_document_count += 1

        if documents or hv_result.records:
            # health_values.csv
            hv_headers = [
                "document_id",
                "biomarker_name",
                "canonical_biomarker_name",
                "value",
                "unit",
                "reference_low",
                "reference_high",
                "confidence",
                "needs_review",
                "is_flagged",
                "flagged_at",
                "flag_reviewed_at",
                "extracted_at",
            ]
            hv_rows = [
                [
                    str(r.document_id),
                    r.biomarker_name,
                    r.canonical_biomarker_name,
                    str(r.value),
                    r.unit or "",
                    str(r.reference_range_low) if r.reference_range_low is not None else "",
                    str(r.reference_range_high) if r.reference_range_high is not None else "",
                    str(r.confidence),
                    str(r.needs_review),
                    str(r.is_flagged),
                    r.flagged_at.isoformat() if r.flagged_at else "",
                    r.flag_reviewed_at.isoformat() if r.flag_reviewed_at else "",
                    r.created_at.isoformat() if r.created_at else "",
                ]
                for r in hv_result.records
            ]
            zf.writestr("health_values.csv", _csv_bytes(hv_headers, hv_rows))

        if documents or ai_result.records:
            # ai_interpretations.csv
            ai_headers = ["document_id", "created_at", "interpretation"]
            ai_rows = [
                [
                    str(entry.document_id) if entry.document_id else "",
                    entry.created_at.isoformat() if entry.created_at else "",
                    entry.interpretation,
                ]
                for entry in ai_result.records
            ]
            zf.writestr("ai_interpretations.csv", _csv_bytes(ai_headers, ai_rows))

        if documents or admin_corrections:
            # admin_corrections.csv
            ac_headers = [
                "document_id",
                "value_name",
                "original_value",
                "new_value",
                "reason",
                "corrected_at",
            ]
            ac_rows = [
                [
                    str(log.document_id) if log.document_id else "",
                    log.value_name,
                    log.original_value,
                    log.new_value,
                    log.reason,
                    log.corrected_at.isoformat() if log.corrected_at else "",
                ]
                for log in admin_corrections
            ]
            zf.writestr("admin_corrections.csv", _csv_bytes(ac_headers, ac_rows))

        # consent_log.csv
        cl_headers = ["consent_type", "consented_at", "privacy_policy_version"]
        cl_rows = [
            [
                log.consent_type,
                log.consented_at.isoformat() if log.consented_at else "",
                log.privacy_policy_version,
            ]
            for log in consent_logs
        ]
        zf.writestr("consent_log.csv", _csv_bytes(cl_headers, cl_rows))

        # summary.txt
        summary = _build_summary(
            user,
            doc_count=exported_doc_count,
            skipped_documents=skipped_document_count,
            hv_count=len(hv_result.records),
            ai_count=len(ai_result.records),
            skipped_health_values=hv_result.skipped_corrupt_records,
            skipped_ai_interpretations=ai_result.skipped_corrupt_records,
        )
        zf.writestr("summary.txt", summary.encode("utf-8", errors="replace"))

    buffer.seek(0)
    return buffer
