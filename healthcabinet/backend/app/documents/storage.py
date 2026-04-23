"""MinIO object storage operations via boto3 S3-compatible API."""

from typing import Any, cast

import boto3
from botocore.config import Config
from botocore.response import StreamingBody

from app.core.config import settings


def get_s3_client() -> "boto3.client":
    # Derive scheme from MINIO_SECURE so the setting actually controls TLS.
    scheme = "https" if settings.MINIO_SECURE else "http"
    endpoint_url = f"{scheme}://{settings.MINIO_ENDPOINT}"
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        region_name="us-east-1",  # MinIO requires a value; arbitrary
        config=Config(signature_version="s3v4"),
    )


def upload_object(
    s3_client: "boto3.client",
    bucket: str,
    s3_key: str,
    content: bytes,
    content_type: str,
) -> None:
    """Upload bytes to MinIO/S3 via server-side proxy (no presigned URL).

    The backend holds the credentials; the browser never talks to MinIO directly.
    """
    s3_client.put_object(Bucket=bucket, Key=s3_key, Body=content, ContentType=content_type)


def delete_object(
    s3_client: "boto3.client",
    bucket: str,
    s3_key: str,
) -> None:
    """Delete an object from MinIO/S3.

    Raises on failure so the caller can roll back the DB transaction.
    """
    s3_client.delete_object(Bucket=bucket, Key=s3_key)


def delete_objects_by_prefix(
    s3_client: "boto3.client",
    bucket: str,
    prefix: str,
) -> int:
    """Delete all objects whose key starts with *prefix*.

    Used as a fallback when the per-object s3_key cannot be decrypted: the key
    format is ``{user_id}/{document_id}/{filename}``, so the prefix
    ``{user_id}/{document_id}/`` reliably scopes deletion to a single document.

    Returns the number of objects deleted. Raises on any S3/network error so
    the caller can log and handle the failure.
    """
    deleted = 0
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objects = page.get("Contents", [])
        if not objects:
            continue
        delete_payload = {"Objects": [{"Key": obj["Key"]} for obj in objects]}
        result = s3_client.delete_objects(Bucket=bucket, Delete=delete_payload)
        errors = result.get("Errors", [])
        if errors:
            raise RuntimeError(
                f"S3 delete_objects returned {len(errors)} error(s): {errors!r}"
            )
        deleted += len(objects)
    return deleted


def get_object_bytes(
    s3_client: "boto3.client",
    bucket: str,
    s3_key: str,
) -> bytes:
    """Read an object from MinIO/S3 into memory for worker-side processing."""
    response = cast(dict[str, Any], s3_client.get_object(Bucket=bucket, Key=s3_key))
    body = cast(StreamingBody, response["Body"])
    try:
        content_length = cast(int | None, response.get("ContentLength"))
        max_bytes = settings.DOCUMENT_PROCESSING_MAX_BYTES
        if content_length is not None and content_length > max_bytes:
            raise ValueError(f"Document exceeds processing size limit of {max_bytes} bytes")

        payload = cast(bytes, body.read(max_bytes + 1))
        if len(payload) > max_bytes:
            raise ValueError(f"Document exceeds processing size limit of {max_bytes} bytes")
        return payload
    finally:
        body.close()
