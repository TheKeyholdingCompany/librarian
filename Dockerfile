# ── Stage 1: Build wheels ──────────────────────────────────
# Wheels-only deps stage means the runtime image never sees gcc / build-essential.
FROM python:3.12-slim AS deps
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt gunicorn

# ── Stage 2: Runtime ──────────────────────────────────────
FROM python:3.12-slim AS runtime
WORKDIR /app

# psycopg[binary] bundles libpq, but installing libpq5 is cheap insurance if
# the dependency is ever swapped for psycopg[c].
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app

COPY --from=deps /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* \
    && rm -rf /wheels

COPY --chown=app:app . .
RUN chmod +x entrypoint.sh

# Materialise the brand asset as a real file. In dev, app/static/brand/logo.svg
# is a symlink to docs/icon.svg (live editing); here we replace it with a copy
# so the runtime image is self-contained and doesn't depend on symlink
# resolution or docs/ surviving in the image. Idempotent: -f removes the
# symlink (or stale copy) first.
RUN rm -f app/static/brand/logo.svg \
    && cp docs/icon.svg app/static/brand/logo.svg \
    && chown app:app app/static/brand/logo.svg

USER app

ENV FLASK_APP=wsgi.py \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    HOST=0.0.0.0

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]
