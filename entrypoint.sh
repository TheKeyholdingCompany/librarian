#!/bin/sh
set -e

# Assemble DATABASE_URL from DB_* envs + the Secrets-Manager-injected
# DB_PASSWORD. Done at start (not in the task definition) so the password
# never appears in `aws ecs describe-task-definition` output or tfstate.
#
# `sslmode=require` is mandatory: RDS enforces TLS by default and psycopg
# opens a plaintext connection unless the URL asks for it explicitly.
export DATABASE_URL="postgresql+psycopg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}?sslmode=require"

# Run Alembic migrations on boot. Two Fargate tasks can race-start during a
# rolling deploy; Alembic's PG advisory lock serialises them so the second
# task sees `head` and no-ops.
flask db upgrade

# `--access-logfile -` writes access logs to stdout so they land in
# CloudWatch via the awslogs driver. 3 sync workers fits 1 vCPU comfortably.
exec gunicorn \
  --bind "${HOST}:${PORT}" \
  --workers 3 \
  --access-logfile - \
  --error-logfile - \
  wsgi:app
