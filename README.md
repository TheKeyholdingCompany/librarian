# tkc-library

A Flask web application backed by PostgreSQL.

- **Backend:** Flask 3 with the application-factory pattern
- **ORM:** SQLAlchemy 2.0 via Flask-SQLAlchemy
- **Migrations:** Alembic via Flask-Migrate
- **Database:** PostgreSQL 16 (in Docker)

---

## Prerequisites

| Tool                     | Version       | Notes                                       |
| ------------------------ | ------------- | ------------------------------------------- |
| Python                   | 3.11 or newer | `python --version`                          |
| Docker + Docker Compose  | v2            | `docker compose version`                    |
| Git                      | any recent    |                                             |

You do **not** need a local PostgreSQL install — it runs in a container.

---

## First-time setup

### 1. Clone and enter the repo

```bash
git clone <repo-url> tkc-library
cd tkc-library
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

The defaults work out-of-the-box with the bundled Docker Compose setup. Edit `.env` only if you change ports, credentials, or want a different `SECRET_KEY`.

| Variable        | Default                                                                  | Purpose                                  |
| --------------- | ------------------------------------------------------------------------ | ---------------------------------------- |
| `FLASK_APP`     | `wsgi.py`                                                                | Tells `flask` which app to load          |
| `FLASK_DEBUG`   | `1`                                                                      | Enables auto-reload + debugger           |
| `SECRET_KEY`    | `change-me-in-production`                                                | Session/CSRF signing key                 |
| `DATABASE_URL`  | `postgresql+psycopg://postgres:postgres@localhost:5521/tkc_library`      | SQLAlchemy connection string            |

### 4. Start PostgreSQL

```bash
docker compose up -d
```

This starts Postgres 16 on host port **5521** (container port 5432) with database `tkc_library`. Verify it's healthy:

```bash
docker compose ps
```

You should see `STATUS  Up ... (healthy)`.

### 5. Initialize the database schema

```bash
flask db init                       # one-time: creates the migrations/ directory
flask db migrate -m "initial"       # autogenerates a migration from the models
flask db upgrade                    # applies it to the database
```

### 6. Run the development server

```bash
flask run --debug
```

Open:

- App: <http://localhost:5000>
- Health check: <http://localhost:5000/health>

---

## Day-to-day workflow

### Activating the environment in a new shell

```bash
source .venv/bin/activate
docker compose up -d                # idempotent — does nothing if already running
flask run --debug
```

### Adding or changing models

1. Edit `app/models.py`.
2. Generate a migration:
   ```bash
   flask db migrate -m "describe the change"
   ```
3. Review the generated file under `migrations/versions/` — Alembic's autogenerate is good but not perfect (it misses index renames, some constraint changes, etc.).
4. Apply it:
   ```bash
   flask db upgrade
   ```

### Adding a Python dependency

```bash
pip install <package>
pip freeze | grep -i <package> >> requirements.txt    # then tidy by hand
```

### Inspecting the database directly

```bash
docker compose exec db psql -U postgres -d tkc_library
```

Or connect from any GUI (TablePlus, DBeaver, pgAdmin) using:

```
host:     localhost
port:     5521
user:     postgres
password: postgres
db:       tkc_library
```

---

## Project layout

```
tkc-library/
├── app/
│   ├── __init__.py        # create_app() factory
│   ├── extensions.py      # db, migrate singletons
│   ├── models.py          # SQLAlchemy models
│   ├── routes.py          # main blueprint
│   └── templates/         # Jinja2 templates
├── migrations/            # Alembic migrations (created by `flask db init`)
├── config.py              # Config class read from env
├── wsgi.py                # entry point for `flask run` / Gunicorn
├── docker-compose.yml     # local Postgres
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Troubleshooting

**`could not connect to server: Connection refused`**
Postgres isn't running or finished starting. Run `docker compose ps` and wait for `(healthy)`.

**`psycopg.OperationalError: ... password authentication failed`**
Your `.env` doesn't match the credentials in `docker-compose.yml`. The defaults are `postgres / postgres`.

**`ModuleNotFoundError: No module named 'psycopg2'`**
SQLAlchemy is defaulting to the old driver. Make sure your `DATABASE_URL` starts with `postgresql+psycopg://` (note the `+psycopg`), not just `postgresql://`.

**`flask db migrate` produces an empty migration**
SQLAlchemy didn't see your model changes. Confirm the model is imported in `app/__init__.py` (the `from app import models` line) and that you saved the file.

**Want to start the database from scratch**
```bash
docker compose down -v              # -v also removes the named volume
docker compose up -d
flask db upgrade
```

---

## Stopping everything

```bash
# stop the dev server with Ctrl+C, then:
docker compose down                 # keeps data
docker compose down -v              # also wipes the database volume
deactivate                          # leave the venv
```
