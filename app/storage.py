"""S3-backed storage helpers for book photos.

The app never reads bytes from S3 — uploads happen browser-side via a
presigned PUT URL, and reads happen anonymously over HTTPS via the public
bucket policy. This module mints the presigned URL and resolves a stored
key back to its public URL.
"""

from __future__ import annotations

from uuid import uuid4

import boto3
from botocore.config import Config as BotoConfig
from flask import current_app

# Mapping of allowed file extensions to the Content-Type we'll sign for.
# Pinning Content-Type at presign time prevents the browser from claiming
# one type to get a URL and then PUTing something else.
ALLOWED_IMAGE_TYPES: dict[str, str] = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
}

UPLOAD_PREFIX = "books/"


class UnsupportedImageType(ValueError):
    """Raised when an extension isn't in ALLOWED_IMAGE_TYPES."""


def _client():
    """Return a boto3 S3 client, cached on the Flask app object.

    Caching here matters: boto3 clients open a connection pool and pay a
    real cost on first construction. Per-request construction would add
    tens of ms to every upload-URL call.
    """
    cached = current_app.extensions.get("s3_client")
    if cached is not None:
        return cached

    cfg = current_app.config
    client = boto3.client(
        "s3",
        region_name=cfg["S3_REGION"],
        endpoint_url=cfg.get("S3_ENDPOINT_URL") or None,
        config=BotoConfig(signature_version="s3v4"),
    )
    current_app.extensions["s3_client"] = client
    return client


def presign_put(extension: str) -> dict[str, str]:
    """Mint a presigned PUT URL for a new image upload.

    Returns ``{"url": <signed url>, "key": <s3 key to store on the model>}``.
    The caller (the browser) must PUT with ``Content-Type`` set to the value
    matching the extension or S3 will reject the request.
    """
    ext = extension.lower().lstrip(".")
    content_type = ALLOWED_IMAGE_TYPES.get(ext)
    if content_type is None:
        raise UnsupportedImageType(ext)

    key = f"{UPLOAD_PREFIX}{uuid4().hex}.{ext}"
    cfg = current_app.config
    url = _client().generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": cfg["S3_BUCKET"],
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=cfg["S3_PRESIGN_TTL_SECONDS"],
        HttpMethod="PUT",
    )
    return {"url": url, "key": key, "content_type": content_type}


def public_url(key: str) -> str:
    """Resolve a stored S3 key to a public HTTPS URL."""
    if not key:
        return ""
    base = current_app.config["S3_PUBLIC_BASE_URL"].rstrip("/")
    return f"{base}/{key}"
