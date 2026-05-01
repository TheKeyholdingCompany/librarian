import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5521/tkc_library",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # S3 image uploads. In prod, these come from the ECS task definition
    # (see terraform/main/modules/ecs). In local dev they point at MinIO via
    # docker-compose — S3_ENDPOINT_URL is the toggle that swaps boto3 between
    # AWS and MinIO with no code changes.
    S3_BUCKET = os.environ.get("S3_BUCKET")
    S3_REGION = os.environ.get("AWS_REGION", "eu-west-1")
    S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL")  # unset in prod
    S3_PUBLIC_BASE_URL = os.environ.get("S3_PUBLIC_BASE_URL")
    S3_PRESIGN_TTL_SECONDS = int(os.environ.get("S3_PRESIGN_TTL_SECONDS", "300"))
