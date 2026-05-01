# ── Bucket ──────────────────────────────────────────────────

resource "aws_s3_bucket" "this" {
  bucket = var.bucket_name

  tags = {
    Name = "${var.name}-${var.env}-uploads"
    env  = var.env
  }
}

# Server-side encryption with S3-managed keys. KMS would add per-request
# cost and a dependency on a CMK with no real benefit for public images.
resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Abort multipart uploads that never complete. Browser PUTs are single-part
# so this is purely defensive against future direct-from-CLI uploads.
resource "aws_s3_bucket_lifecycle_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    id     = "abort-incomplete-multipart"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# ── Public access ───────────────────────────────────────────
#
# We want anonymous GET on books/*, nothing else. The modern way is:
#  - Disable account-level ACL pathways (block_public_acls, ignore_public_acls).
#  - Allow public *bucket policies* (block_public_policy=false, restrict_public_buckets=false)
#    so the resource policy below actually takes effect.

resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = false
  restrict_public_buckets = false
}

data "aws_iam_policy_document" "public_read" {
  statement {
    sid     = "PublicReadOnPrefix"
    effect  = "Allow"
    actions = ["s3:GetObject"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    resources = ["${aws_s3_bucket.this.arn}/${var.public_read_prefix}*"]
  }
}

resource "aws_s3_bucket_policy" "this" {
  bucket = aws_s3_bucket.this.id
  policy = data.aws_iam_policy_document.public_read.json

  # The bucket policy is rejected by S3 if BPA is still blocking public
  # policies at the moment of PutBucketPolicy.
  depends_on = [aws_s3_bucket_public_access_block.this]
}

# ── CORS ────────────────────────────────────────────────────
#
# Required for browser-side presigned PUTs. The presigned URL itself is the
# capability — anyone with it can upload, regardless of CORS — so '*' here
# does not weaken security; it just prevents the browser from blocking the
# response.

resource "aws_s3_bucket_cors_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  cors_rule {
    allowed_methods = ["PUT", "GET", "HEAD"]
    allowed_origins = var.cors_allowed_origins
    allowed_headers = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# ── IAM policy for upload (consumed by ECS task role) ───────
#
# Scoped to PutObject on the public_read_prefix only. The app never needs
# GetObject (reads happen anonymously over HTTPS) and never needs Delete
# (we don't delete book covers from the running app).

data "aws_iam_policy_document" "put_object" {
  statement {
    sid       = "PutObjectsUnderPrefix"
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.this.arn}/${var.public_read_prefix}*"]
  }
}

resource "aws_iam_policy" "put_object" {
  name        = "${var.name}-${var.env}-s3-uploads-put"
  description = "Allows the ${var.name} ECS task to PUT objects into the uploads bucket under ${var.public_read_prefix}"
  policy      = data.aws_iam_policy_document.put_object.json
}
