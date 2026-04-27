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

## Web 101 for Python folks

If you've only written Python *scripts* (a file you run with `python foo.py` that prints something and exits), the Flask tutorial below will use a handful of words you may not have a mental model for yet. This section gives you that model in ~5 minutes. **Skip it if you've already built websites in any language.**

### Clients, servers, and HTTP

A normal Python script runs top-to-bottom and exits. A *web server* is the opposite: it's a program that **starts up and waits forever**, doing nothing until something asks it for a page. That "something" is usually a browser.

The conversation looks like this:

```
Browser  ──── "GET /about HTTP/1.1" ───▶  Server (your Flask app)
Browser  ◀─── "200 OK\n\n<html>..."  ───  Server
```

- **Request:** the browser sends a short text message saying *which URL it wants* (`/about`) and *what it wants to do* (`GET` = read, `POST` = submit data).
- **Response:** your server sends back a status code (`200` = ok, `404` = not found, `500` = your code crashed) plus the page contents.

This is **HTTP**. Every page load, every form submission, every API call — same pattern.

### Why `flask run` doesn't return your terminal

Because the server has to keep waiting for the next request. That's the job. Hit `Ctrl+C` to stop it. While it's running, every browser request causes Flask to call one of your Python functions, get the return value, and send it back. Your script-shaped intuition ("function returns → program ends") doesn't apply: in a server, your functions are called *over and over*, once per request.

In debug mode (`flask run --debug`), Flask also watches your `.py` files and restarts the process when you save — that's why edits "just work" without you stopping and starting it.

### Decorators in 60 seconds

You'll see this everywhere in Flask:

```python
@bp.route("/about")
def about():
    return "hello"
```

The `@bp.route("/about")` line is a **decorator**. It's exactly equivalent to:

```python
def about():
    return "hello"
about = bp.route("/about")(about)
```

Read it as: *"register this function as the handler for `/about`"*. The decorator doesn't change what `about()` does — it just **tells Flask the function exists** and which URL should call it. If you delete the `@bp.route(...)` line, the function still works as a plain Python function; Flask just won't know to call it for any URL.

### HTML and forms, just enough

**HTML** is the text format browsers render as a page. Tags wrap content: `<h1>Hi</h1>` becomes a heading, `<p>...</p>` becomes a paragraph. You don't need to memorize tags — copy from the tutorial and adjust.

A **form** is the standard way for a browser to send data *to* your server:

```html
<form method="POST" action="/items">
  <input type="text" name="name" />
  <button type="submit">Save</button>
</form>
```

When the user clicks the button:

1. The browser collects every `<input>` inside the form, keyed by its `name` attribute.
2. It sends a `POST` request to the URL in `action=` with that data attached.
3. Flask gives your view function access to the data via `request.form["name"]`.

The `name="..."` attribute is the *only* link between the HTML field and the Python code — get it wrong and `request.form` won't have your value. This is the most common beginner bug.

### Databases in 90 seconds

A **relational database** (PostgreSQL, in our case) stores data in **tables**. A table is conceptually a spreadsheet:

| id | name        | created_at          |
| -- | ----------- | ------------------- |
| 1  | First book  | 2026-04-27 10:30:00 |
| 2  | Second book | 2026-04-27 10:31:00 |

- Each **row** is one record (one book, one user, one order).
- Each **column** has a fixed type (`integer`, `text`, `timestamp`, …).
- The **primary key** (almost always called `id`) is a column whose value is unique for every row. It's how you say "give me the row that *is* this thing" rather than "give me rows where the name happens to be 'X'".

You normally talk to the database in **SQL** (`SELECT * FROM items WHERE id = 1`), but in this project we use an **ORM** (SQLAlchemy) that lets you write Python instead and turns it into SQL behind the scenes. So `db.session.get(Item, 1)` *becomes* roughly `SELECT * FROM items WHERE id = 1` when it actually runs.

One last concept: **transactions**. When you create or change rows, the change isn't saved until you call `db.session.commit()`. Until then, it's pending — visible to your code but not actually written. If anything goes wrong before the commit, calling `db.session.rollback()` (or just letting the request fail) throws away the pending changes. This means a half-finished operation can never leave the database in a partial state.

That's the whole conceptual stack you need. On to building.

---

## Flask tutorial

If you skipped "Web 101" above and haven't done any web programming before, scroll back up — this section assumes you know what HTTP, HTML forms, and database rows are. Each step modifies files already in this project — copy, paste, save, refresh the browser.

### The 60-second mental model

When a request hits the server, Flask:

1. **Matches the URL** against routes you registered (e.g., `/`, `/items/42`).
2. **Calls your view function** — a regular Python function that returns either a string (HTML), a dict (auto-serialized to JSON), or a `Response` object.
3. **Sends that back** to the browser.

Two more concepts to internalize:

- **Blueprints** are how Flask groups routes. You've already got one in `app/routes.py` (`bp = Blueprint("main", __name__)`). Think of a blueprint as a "module of URLs" that gets attached to the app inside `create_app()`.
- **Templates** are Jinja2 HTML files in `app/templates/`. `render_template("foo.html", x=1)` loads `foo.html` and makes `x` available as a variable inside `{{ ... }}` tags.

### Tutorial 1 — Add a new page

Goal: a page at `/about` that says "About this site".

**Step 1.** Add a view function to `app/routes.py`:

```python
@bp.route("/about")
def about():
    return render_template("about.html")
```

**Step 2.** Create `app/templates/about.html`:

```html
<!doctype html>
<html>
  <head><title>About</title></head>
  <body>
    <h1>About this site</h1>
    <p>Built with Flask and PostgreSQL.</p>
  </body>
</html>
```

**Step 3.** With `flask run --debug` already running, just visit <http://localhost:5000/about>. Debug mode auto-reloads on file changes — no restart needed.

That's the whole loop: **route → view → template**.

### Tutorial 2 — Read from the database

Goal: a page at `/items` listing every `Item` row.

The model is already defined in `app/models.py` — we'll just query it.

**Step 1.** Add the route to `app/routes.py`:

```python
@bp.route("/items")
def list_items():
    items = db.session.scalars(
        db.select(Item).order_by(Item.created_at.desc())
    ).all()
    return render_template("items.html", items=items)
```

What's happening line by line:

- `db.select(Item)` builds a SQL `SELECT * FROM items` (without executing it).
- `.order_by(Item.created_at.desc())` adds an `ORDER BY`.
- `db.session.scalars(...)` runs it and returns model objects (not raw tuples).
- `.all()` materializes them into a list.

**Step 2.** Create `app/templates/items.html`:

```html
<!doctype html>
<html>
  <body>
    <h1>Items</h1>
    <ul>
      {% for item in items %}
        <li>{{ item.name }} — {{ item.created_at.strftime('%Y-%m-%d') }}</li>
      {% else %}
        <li>No items yet.</li>
      {% endfor %}
    </ul>
  </body>
</html>
```

Jinja2 syntax: `{{ ... }}` prints, `{% ... %}` controls flow. The `{% else %}` inside `{% for %}` runs when the iterable is empty — a Jinja-specific touch.

**Step 3.** Visit <http://localhost:5000/items>. You'll see "No items yet" — let's fix that next.

### Tutorial 3 — Write to the database (a form)

Goal: a form at `/items/new` that creates an `Item`.

**Step 1.** Add two routes — one to show the form, one to handle submission:

```python
from flask import redirect, request, url_for

@bp.route("/items/new", methods=["GET"])
def new_item_form():
    return render_template("new_item.html")

@bp.route("/items", methods=["POST"])
def create_item():
    name = request.form["name"].strip()
    if not name:
        return redirect(url_for("main.new_item_form"))

    item = Item(name=name)
    db.session.add(item)
    db.session.commit()
    return redirect(url_for("main.list_items"))
```

Three Flask-specific concepts here:

- **`request.form`** is a dict-like object holding submitted form fields (the `name="..."` attributes on `<input>` tags).
- **`db.session.add()` + `commit()`** is the SQLAlchemy unit-of-work pattern: stage changes, then flush them in one transaction. If `commit()` raises, nothing is saved.
- **`url_for("main.list_items")`** generates the URL for a view by *name*, not by hardcoding the path. The `main.` prefix is the blueprint name. This means renaming `/items` to `/library/items` later only requires changing the route decorator — every `url_for` call updates automatically.

**Step 2.** Create `app/templates/new_item.html`:

```html
<!doctype html>
<html>
  <body>
    <h1>New item</h1>
    <form method="POST" action="{{ url_for('main.create_item') }}">
      <input type="text" name="name" required />
      <button type="submit">Create</button>
    </form>
  </body>
</html>
```

**Step 3.** Visit <http://localhost:5000/items/new>, submit the form, and you'll be redirected back to `/items` with your new entry.

> **Why GET-then-POST-then-redirect?** The "Post/Redirect/Get" pattern stops the browser from re-submitting the form if the user hits refresh after creating an item. Always redirect after a successful POST.

### Tutorial 4 — URL parameters (a detail page)

Goal: `/items/<id>` shows a single item.

```python
from flask import abort

@bp.route("/items/<int:item_id>")
def show_item(item_id):
    item = db.session.get(Item, item_id)
    if item is None:
        abort(404)
    return render_template("item_detail.html", item=item)
```

The `<int:item_id>` syntax does two things:

1. **Captures** the URL segment and passes it as the `item_id` argument.
2. **Validates** it as an integer — `/items/abc` returns a 404 automatically without your function ever running.

Other built-in converters: `<string:>`, `<float:>`, `<uuid:>`, `<path:>` (allows slashes).

`db.session.get(Item, item_id)` is the optimized "get by primary key" query — it checks the SQLAlchemy identity map first and only hits the database if the object isn't already loaded.

`abort(404)` short-circuits the request and returns a 404 response. You can customize 404 pages later with an `@app.errorhandler(404)`.

### Where to go next

- **Forms with validation:** install `Flask-WTF` for CSRF protection and declarative form classes.
- **User accounts:** `Flask-Login` handles the session/cookie machinery; pair it with `passlib` for password hashing.
- **JSON APIs:** any view function that returns a `dict` is auto-converted to a JSON response with the right `Content-Type`. For more complex needs, look at `Flask-RESTful` or just use plain Flask with `jsonify()`.
- **Tests:** Flask provides `app.test_client()` — use the application factory's testing config to point at a separate test database, then make requests like `client.get("/items")` and assert on `response.status_code` / `response.data`.

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
