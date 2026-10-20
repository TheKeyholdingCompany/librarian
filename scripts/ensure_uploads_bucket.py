"""Create the local dev uploads bucket with the access rules prod gets from Terraform.

Local dev only — refuses to run without S3_ENDPOINT_URL, so it can never
reach the real bucket, which terraform/main/modules/s3_uploads owns.

The compose stack used to do this with an `mc` sidecar against MinIO. RustFS
creates no bucket and, unlike MinIO, answers no CORS preflight until a bucket
carries a rule, so both the public-read policy (anonymous GET on books/*, how
the browser loads every cover) and the CORS rule (how the browser completes a
presigned PUT) have to be applied explicitly.

Usage::

    S3_BUCKET=... S3_ENDPOINT_URL=http://localhost:9000 \\
        python scripts/ensure_uploads_bucket.py

Idempotent: safe to re-run on every `docker compose up`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app import create_app  # noqa: E402
from app.storage import UPLOAD_PREFIX  # noqa: E402

CORS_RULES = [
    {
        "AllowedMethods": ["PUT", "GET", "HEAD"],
        "AllowedOrigins": ["*"],
        "AllowedHeaders": ["*"],
        "ExposeHeaders": ["ETag"],
        "MaxAgeSeconds": 3000,
    }
]


def public_read_policy(bucket: str) -> str:
    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadOnPrefix",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket}/{UPLOAD_PREFIX}*",
                }
            ],
        }
    )


def provision(s3, bucket: str) -> None:
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError as err:
        if err.response["Error"]["Code"] not in {"404", "NoSuchBucket"}:
            raise
        s3.create_bucket(Bucket=bucket)
    s3.put_bucket_policy(Bucket=bucket, Policy=public_read_policy(bucket))
    s3.put_bucket_cors(Bucket=bucket, CORSConfiguration={"CORSRules": CORS_RULES})


def main() -> int:
    app = create_app()
    endpoint = app.config.get("S3_ENDPOINT_URL")
    if not endpoint:
        print("S3_ENDPOINT_URL is unset — this script only provisions the local store.")
        return 1
    bucket = app.config.get("S3_BUCKET")
    if not bucket:
        print("S3_BUCKET is unset — nothing to provision.")
        return 1

    s3 = boto3.client("s3", region_name=app.config["S3_REGION"], endpoint_url=endpoint)
    try:
        provision(s3, bucket)
    except EndpointConnectionError:
        print(f"{endpoint} is unreachable — start it with `docker compose up -d`.")
        return 1
    print(f"Bucket ready: {bucket} at {endpoint} (public read on {UPLOAD_PREFIX}*, CORS set)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
