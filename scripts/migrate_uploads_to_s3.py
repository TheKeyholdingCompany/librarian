"""One-shot: copy app/static/uploads/* to S3 and prefix existing DB rows.

Runs once per environment as part of the disk -> S3 cutover. Idempotent —
re-running uploads only objects S3 doesn't already have, and updates only
DB rows that don't yet carry the ``books/`` prefix.

Usage::

    DATABASE_URL=... S3_BUCKET=... AWS_REGION=... \\
        python scripts/migrate_uploads_to_s3.py

Optional env:
    S3_ENDPOINT_URL   point at MinIO/LocalStack instead of AWS
    DRY_RUN=1         report what would happen without writing
"""

from __future__ import annotations

import mimetypes
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Book  # noqa: E402
from app.storage import UPLOAD_PREFIX  # noqa: E402

UPLOADS_DIR = REPO_ROOT / "app" / "static" / "uploads"
DRY_RUN = os.environ.get("DRY_RUN") == "1"


def _s3_client(app):
    return boto3.client(
        "s3",
        region_name=app.config["S3_REGION"],
        endpoint_url=app.config.get("S3_ENDPOINT_URL") or None,
    )


def _exists(s3, bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def upload_files(app) -> int:
    if not UPLOADS_DIR.is_dir():
        print(f"No uploads directory at {UPLOADS_DIR} — nothing to copy.")
        return 0

    bucket = app.config["S3_BUCKET"]
    s3 = _s3_client(app)
    uploaded = 0

    for path in sorted(UPLOADS_DIR.iterdir()):
        if not path.is_file():
            continue
        key = f"{UPLOAD_PREFIX}{path.name}"
        if _exists(s3, bucket, key):
            print(f"  skip (exists): {key}")
            continue
        content_type, _ = mimetypes.guess_type(path.name)
        if DRY_RUN:
            print(f"  would upload: {path} -> s3://{bucket}/{key} ({content_type})")
            continue
        with path.open("rb") as fh:
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=fh,
                ContentType=content_type or "application/octet-stream",
            )
        print(f"  uploaded: {key}")
        uploaded += 1
    return uploaded


def prefix_db_rows(app) -> int:
    """Prepend ``books/`` to photo_filename rows that don't already carry it."""
    with app.app_context():
        rows = db.session.scalars(db.select(Book).where(Book.photo_filename.isnot(None))).all()
        to_update = [b for b in rows if not b.photo_filename.startswith(UPLOAD_PREFIX)]

        if DRY_RUN:
            for b in to_update:
                print(f"  would update Book {b.id}: {b.photo_filename!r} -> {UPLOAD_PREFIX + b.photo_filename!r}")
            return len(to_update)

        if not to_update:
            return 0

        for b in to_update:
            b.photo_filename = UPLOAD_PREFIX + b.photo_filename
        db.session.commit()
        return len(to_update)


def main() -> int:
    app = create_app()
    if not app.config.get("S3_BUCKET"):
        print("S3_BUCKET is not set; aborting.", file=sys.stderr)
        return 1

    mode = "DRY RUN" if DRY_RUN else "LIVE"
    print(f"== Migrating uploads to S3 [{mode}] ==")
    print(f"   bucket: {app.config['S3_BUCKET']}")
    print(f"   region: {app.config['S3_REGION']}")
    if app.config.get("S3_ENDPOINT_URL"):
        print(f"   endpoint: {app.config['S3_ENDPOINT_URL']}")

    n_uploaded = upload_files(app)
    n_updated = prefix_db_rows(app)

    print(f"\nDone. Uploaded {n_uploaded} object(s); updated {n_updated} DB row(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
