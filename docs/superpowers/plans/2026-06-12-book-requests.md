# Book Requests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let any logged-in user request a new book (title, author, link); requests queue for admin review, and approving one prefills the existing Add Book form.

**Architecture:** A new `BookRequest` SQLAlchemy model + Alembic migration. The submit form/route lives in the `library` blueprint; the admin review page and reject route live in the `admin` blueprint. Approve is a link to the existing `library.add_book` route with a `?request_id=N` query param — `add_book` prefills from the request on GET and marks it `approved` only when the book is actually saved.

**Tech Stack:** Flask blueprints, Flask-WTF/WTForms, SQLAlchemy 2.0 style queries, Alembic (Flask-Migrate), Jinja2 templates.

**Spec:** `docs/superpowers/specs/2026-06-12-book-requests-design.md`

**Note on testing:** This repo has no automated test framework wired up (only `test_db.py`). Per the approved spec, verification is manual. Each task ends with concrete manual verification steps and a commit.

---

### Task 1: `BookRequest` model + migration

**Files:**
- Modify: `app/models.py` (append new model; `datetime`/`timezone` already imported at top)
- Create: `migrations/versions/a1b2c3d4e5f6_add_book_requests_table.py`

- [ ] **Step 1: Add the model**

Append to `app/models.py`:

```python
class BookRequest(db.Model):
    __tablename__ = "book_requests"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    author = db.Column(db.String(120), nullable=False)
    link = db.Column(db.String(500), nullable=False)
    requested_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)  # pending | approved | rejected
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    reviewed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Two FKs point at users.id, so SQLAlchemy needs explicit foreign_keys to
    # tell the requester relationship apart from the reviewer one.
    requester = db.relationship("User", foreign_keys=[requested_by_user_id])
    reviewer = db.relationship("User", foreign_keys=[reviewed_by_user_id])

    def __repr__(self):
        return f"<BookRequest {self.id} {self.title!r} status={self.status}>"
```

- [ ] **Step 2: Create the migration**

Create `migrations/versions/a1b2c3d4e5f6_add_book_requests_table.py`:

```python
"""add book_requests table

Revision ID: a1b2c3d4e5f6
Revises: d1f5a2b9c0e4
Create Date: 2026-06-12 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'd1f5a2b9c0e4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'book_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=120), nullable=False),
        sa.Column('author', sa.String(length=120), nullable=False),
        sa.Column('link', sa.String(length=500), nullable=False),
        sa.Column('requested_by_user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by_user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('book_requests')
```

- [ ] **Step 3: Apply the migration**

Run (DB must be up — `docker compose up -d db` if needed):

```bash
source .venv/bin/activate
flask db upgrade
```

Expected: alembic logs `Running upgrade d1f5a2b9c0e4 -> a1b2c3d4e5f6, add book_requests table`.

- [ ] **Step 4: Verify head + table**

Run:

```bash
flask db current
```

Expected: shows `a1b2c3d4e5f6 (head)`.

- [ ] **Step 5: Commit**

```bash
git add app/models.py migrations/versions/a1b2c3d4e5f6_add_book_requests_table.py
git commit -m "feat(requests): add BookRequest model and migration"
```

---

### Task 2: `RequestBookForm`

**Files:**
- Modify: `app/forms.py`

- [ ] **Step 1: Add the URL validator to imports**

In `app/forms.py`, change the validators import line to include `URL`:

```python
from wtforms.validators import DataRequired, Length, Optional, Regexp, URL
```

- [ ] **Step 2: Add the form**

Append to `app/forms.py`:

```python
class RequestBookForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(min=1, max=120)])
    author = StringField("Author", validators=[DataRequired(), Length(min=1, max=120)])
    link = StringField(
        "Link",
        validators=[DataRequired(), URL(message="Enter a valid URL (including http:// or https://)."), Length(max=500)],
    )
    submit = SubmitField("Submit Request")
```

- [ ] **Step 3: Verify it imports**

Run:

```bash
source .venv/bin/activate
python -c "from app.forms import RequestBookForm; print('ok', [f for f in RequestBookForm()._fields])"
```

Expected: `ok ['title', 'author', 'link', 'submit', 'csrf_token']` (order may vary; all four named fields present).

- [ ] **Step 4: Commit**

```bash
git add app/forms.py
git commit -m "feat(requests): add RequestBookForm"
```

---

### Task 3: Submit route + template + library index link

**Files:**
- Modify: `app/library/routes.py`
- Create: `app/library/templates/library/request_book.html`
- Modify: `app/library/templates/library/index.html` (add link near `.actions`, ~line 308-312)

- [ ] **Step 1: Import the form and model**

In `app/library/routes.py`, update the two import lines:

```python
from app.forms import BookForm, RequestBookForm
from app.models import Book, Borrow, User, Rating, BookRequest
```

- [ ] **Step 2: Add the submit route**

Add to `app/library/routes.py` (e.g. after `index`):

```python
@bp.route("/request", methods=["GET", "POST"])
@login_required
def request_book():
    form = RequestBookForm()
    if form.validate_on_submit():
        book_request = BookRequest(
            title=form.title.data,
            author=form.author.data,
            link=form.link.data,
            requested_by_user_id=session.get("user_id"),
            status="pending",
        )
        db.session.add(book_request)
        db.session.commit()
        flash("Thanks! Your book request has been submitted for review.", "success")
        return redirect(url_for("library.index"))
    return render_template("library/request_book.html", form=form)
```

- [ ] **Step 3: Create the template**

Create `app/library/templates/library/request_book.html`:

```html
{% extends "base.html" %}

{% block title %}Request a Book — Librarian{% endblock %}

{% block extra_styles %}
<style>
  .brand { margin-bottom: 1.5rem; }
  h1 { margin-top: 0; }
  .form-group { margin-bottom: 1.25rem; }
  .form-group label { display: block; font-weight: 600; margin-bottom: 0.35rem; }
  .form-control {
    width: 100%;
    padding: 0.65rem 0.85rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 1rem;
    font-family: inherit;
    color: var(--text);
    background: white;
  }
  .errors { color: #b3261e; font-size: 0.85rem; margin: 0.35rem 0 0; list-style: none; padding: 0; }
  .submit-btn {
    padding: 0.75rem 1.5rem;
    background: var(--brand);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
  }
  .submit-btn:hover { background: var(--brand-dark); }
</style>
{% endblock %}

{% block content %}
<div class="container">
  {% include "_brand.html" %}
  <div class="card">
    <h1>Request a Book</h1>
    <p class="muted">Suggest a book for the library. An admin will review your request.</p>

    <form method="POST" novalidate>
      {{ form.hidden_tag() }}

      <div class="form-group">
        {{ form.title.label }}
        {{ form.title(class="form-control") }}
        {% if form.title.errors %}
          <ul class="errors">{% for e in form.title.errors %}<li>{{ e }}</li>{% endfor %}</ul>
        {% endif %}
      </div>

      <div class="form-group">
        {{ form.author.label }}
        {{ form.author(class="form-control") }}
        {% if form.author.errors %}
          <ul class="errors">{% for e in form.author.errors %}<li>{{ e }}</li>{% endfor %}</ul>
        {% endif %}
      </div>

      <div class="form-group">
        {{ form.link.label }}
        {{ form.link(class="form-control", placeholder="https://...") }}
        {% if form.link.errors %}
          <ul class="errors">{% for e in form.link.errors %}<li>{{ e }}</li>{% endfor %}</ul>
        {% endif %}
      </div>

      {{ form.submit(class="submit-btn") }}
      <a href="{{ url_for('library.index') }}" style="margin-left: 1rem;">Cancel</a>
    </form>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Add a "Request a Book" link on the index page**

In `app/library/templates/library/index.html`, the admin-only Add Book block is:

```html
    {% if session.get('role') == 'admin' %}
    <div class="actions">
      <a href="{{ url_for('library.add_book') }}">+ Add Book</a>
    </div>
    {% endif %}
```

Add a request link visible to everyone immediately after that `{% endif %}`:

```html
    <div class="actions">
      <a href="{{ url_for('library.request_book') }}">+ Request a Book</a>
    </div>
```

- [ ] **Step 5: Verify manually**

Run the app (`docker compose up` per README) and, logged in as any user, visit `/`. Confirm the "+ Request a Book" button shows. Click it, submit a valid title/author/link → expect redirect to `/` with the green "Thanks! Your book request has been submitted for review." flash. Submit with an invalid link (e.g. `notaurl`) → expect the URL validation error to render under the Link field.

- [ ] **Step 6: Commit**

```bash
git add app/library/routes.py app/library/templates/library/request_book.html app/library/templates/library/index.html
git commit -m "feat(requests): add book request submit form and route"
```

---

### Task 4: Admin review page + reject route + dashboard link

**Files:**
- Modify: `app/admin/routes.py`
- Create: `app/admin/templates/admin/requests.html`
- Modify: `app/admin/templates/admin/dashboard.html`

- [ ] **Step 1: Update imports and the dashboard route**

In `app/admin/routes.py`, update imports:

```python
from datetime import datetime, timezone

from flask import flash, redirect, render_template, session, url_for
from sqlalchemy.orm import selectinload

from app.admin import bp
from app.auth import admin_required
from app.extensions import db
from app.models import Borrow, User, BookRequest
```

Replace the existing `dashboard` view so it passes a pending count:

```python
@bp.route("/admin")
@admin_required
def dashboard():
    username = session.get("username")
    user = db.session.scalar(
        db.select(User)
        .options(selectinload(User.favorites))
        .where(User.username == username)
    )
    pending_request_count = db.session.scalar(
        db.select(db.func.count())
        .select_from(BookRequest)
        .where(BookRequest.status == "pending")
    )
    return render_template(
        "admin/dashboard.html",
        user=user,
        pending_request_count=pending_request_count,
    )
```

- [ ] **Step 2: Add the review-list and reject routes**

Append to `app/admin/routes.py`:

```python
@bp.route("/admin/requests")
@admin_required
def book_requests():
    requests = db.session.scalars(
        db.select(BookRequest)
        .options(
            selectinload(BookRequest.requester),
            selectinload(BookRequest.reviewer),
        )
        .order_by(BookRequest.created_at.desc())
    ).all()
    # Pending first, then approved, then rejected. Python's sort is stable, so
    # the created_at-desc order is preserved within each status group.
    status_order = {"pending": 0, "approved": 1, "rejected": 2}
    requests = sorted(requests, key=lambda r: status_order.get(r.status, 3))
    return render_template("admin/requests.html", requests=requests)


@bp.route("/admin/requests/<int:request_id>/reject", methods=["POST"])
@admin_required
def reject_request(request_id):
    book_request = db.session.get(BookRequest, request_id)
    if not book_request:
        flash("Request not found.", "error")
        return redirect(url_for("admin.book_requests"))
    if book_request.status != "pending":
        flash("That request has already been reviewed.", "info")
        return redirect(url_for("admin.book_requests"))

    book_request.status = "rejected"
    book_request.reviewed_at = datetime.now(timezone.utc)
    book_request.reviewed_by_user_id = session.get("user_id")
    db.session.commit()
    flash(f"Request for '{book_request.title}' rejected.", "success")
    return redirect(url_for("admin.book_requests"))
```

- [ ] **Step 3: Create the review template**

Create `app/admin/templates/admin/requests.html`:

```html
{% extends "base.html" %}

{% block title %}Book Requests — Librarian{% endblock %}

{% block extra_styles %}
<style>
  .brand { margin-bottom: 1.5rem; }
  h1 { margin-top: 0; }
  table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
  th, td { text-align: left; padding: 0.6rem 0.75rem; border-bottom: 1px solid var(--border); vertical-align: top; }
  th { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.03em; color: var(--muted); }
  .status { font-weight: 600; text-transform: capitalize; }
  .status.pending { color: #b06a00; }
  .status.approved { color: #1a7f37; }
  .status.rejected { color: #b3261e; }
  .row-actions { display: flex; gap: 0.5rem; }
  .btn {
    display: inline-block;
    padding: 0.4rem 0.8rem;
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 600;
    border: none;
    cursor: pointer;
    text-decoration: none;
  }
  .btn-approve { background: var(--brand); color: white; }
  .btn-approve:hover { background: var(--brand-dark); text-decoration: none; }
  .btn-reject { background: #f0f1f4; color: #b3261e; }
  .btn-reject:hover { background: #e6e7ea; }
</style>
{% endblock %}

{% block content %}
<div class="container">
  {% include "_brand.html" %}
  <div class="card">
    <h1>Book Requests</h1>
    <p><a href="{{ url_for('admin.dashboard') }}">← Back to admin dashboard</a></p>

    {% if requests %}
    <table>
      <thead>
        <tr>
          <th>Title</th>
          <th>Author</th>
          <th>Link</th>
          <th>Requested by</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {% for r in requests %}
        <tr>
          <td>{{ r.title }}</td>
          <td>{{ r.author }}</td>
          <td><a href="{{ r.link }}" target="_blank" rel="noopener">link</a></td>
          <td>{{ r.requester.username if r.requester else "—" }}</td>
          <td><span class="status {{ r.status }}">{{ r.status }}</span></td>
          <td>
            {% if r.status == "pending" %}
            <div class="row-actions">
              <a class="btn btn-approve" href="{{ url_for('library.add_book', request_id=r.id) }}">Approve</a>
              <form method="POST" action="{{ url_for('admin.reject_request', request_id=r.id) }}">
                {# Bare token: this template has no FlaskForm, but CSRF protection still applies. #}
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <button type="submit" class="btn btn-reject">Reject</button>
              </form>
            </div>
            {% else %}
            <span class="muted">Reviewed{% if r.reviewer %} by {{ r.reviewer.username }}{% endif %}</span>
            {% endif %}
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
    <p class="muted">No book requests yet.</p>
    {% endif %}
  </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Add the dashboard link**

In `app/admin/templates/admin/dashboard.html`, add this paragraph immediately after the existing "Borrower Dashboard" `<p>` line (the one linking to `admin.borrowers`):

```html
    <p><a href="{{ url_for('admin.book_requests') }}">Review Book Requests</a> — Approve or reject books suggested by borrowers.{% if pending_request_count %} <strong>({{ pending_request_count }} pending)</strong>{% endif %}</p>
```

- [ ] **Step 5: Verify `csrf_token()` is available in templates**

The app uses Flask-WTF, which registers a global `csrf_token()` for Jinja. Confirm:

```bash
source .venv/bin/activate
python -c "from app import create_app; from flask_wtf.csrf import generate_csrf; a=create_app();
import flask_wtf; print('flask_wtf', flask_wtf.__version__)"
```

Expected: prints a flask_wtf version with no import error. (If `csrf_token()` is not globally available at render time, the reject form will raise `Undefined`; in that case wrap the page in a minimal `FlaskForm` instead — but Flask-WTF registers it globally by default.)

- [ ] **Step 6: Verify manually**

As admin, open `/admin` → confirm the "Review Book Requests" link shows, with "(N pending)" if a pending request from Task 3 exists. Click it → `/admin/requests` lists the request with a working external link, the requester's username, status "pending", and Approve/Reject buttons. Click **Reject** → expect redirect back with "Request for '…' rejected." and the row's status now showing "rejected" with no action buttons.

- [ ] **Step 7: Commit**

```bash
git add app/admin/routes.py app/admin/templates/admin/requests.html app/admin/templates/admin/dashboard.html
git commit -m "feat(requests): add admin review page and reject action"
```

---

### Task 5: Approve handoff — prefill + mark approved in `library.add_book`

**Files:**
- Modify: `app/library/routes.py` (the `add_book` view)
- Modify: `app/library/templates/library/add_book.html` (add prefill banner)

- [ ] **Step 1: Update the `add_book` view**

Replace the existing `add_book` view in `app/library/routes.py` with:

```python
@bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_book():
    # When reached via an admin "Approve" link the URL carries ?request_id=N.
    # The form has no explicit action, so it posts back to this same URL with
    # the query string intact — request_id survives the GET→POST round trip.
    request_id = request.args.get("request_id", type=int)
    book_request = db.session.get(BookRequest, request_id) if request_id else None
    # Only honour a request that still exists and hasn't been decided yet.
    if book_request and book_request.status != "pending":
        book_request = None

    form = BookForm()
    form.submit.label.text = "Add Book"
    if form.validate_on_submit():
        book = Book(
            name=form.name.data,
            description=form.description.data,
            photo_filename=form.photo_key.data or None,
        )
        db.session.add(book)
        # The request flips to approved only once the book is actually saved;
        # abandoning this form leaves it pending.
        if book_request:
            book_request.status = "approved"
            book_request.reviewed_at = datetime.now(timezone.utc)
            book_request.reviewed_by_user_id = session.get("user_id")
        db.session.commit()
        flash(f"Book '{book.name}' added successfully!", "success")
        return redirect(url_for("library.index"))

    # Prefill from the request on first render only — don't clobber what the
    # admin typed if validation bounced the POST back.
    if book_request and request.method == "GET":
        form.name.data = book_request.title
        form.description.data = f"By {book_request.author}\n{book_request.link}"

    return render_template(
        "library/add_book.html",
        form=form,
        form_title="Add a New Book",
        allowed_extensions=sorted(ALLOWED_IMAGE_TYPES.keys()),
        book_request=book_request,
    )
```

- [ ] **Step 2: Add the prefill banner to the template**

In `app/library/templates/library/add_book.html`, the form card opens with:

```html
  <div class="card">
    <h1>{{ form_title or 'Add a New Book' }}</h1>
    
    <form method="POST" novalidate id="add-book-form">
```

Insert a banner between the `<h1>` and the `<form>`:

```html
    {% if book_request %}
    <p class="muted" style="margin-top: 0;">
      Creating a book from a request by <strong>{{ book_request.requester.username if book_request.requester else "a borrower" }}</strong>.
      Original link: <a href="{{ book_request.link }}" target="_blank" rel="noopener">{{ book_request.link }}</a>
    </p>
    {% endif %}
```

- [ ] **Step 3: Verify the approve→save path**

As admin, go to `/admin/requests`, click **Approve** on a pending request. Confirm:
- The Add Book form shows the banner ("Creating a book from a request by …") and is prefilled: Name = the requested title, Description = `By {author}` then the link on the next line.
- Save the form. Expect redirect to `/` with "Book '…' added successfully!", the new book visible in the grid, and back on `/admin/requests` that request now showing status "approved" (reviewer = you).

- [ ] **Step 4: Verify the abandon path**

Click **Approve** on another pending request, then navigate away without saving (go to `/`). Reopen `/admin/requests` → confirm that request is still "pending".

- [ ] **Step 5: Verify the stale-id path**

Manually visit `/add?request_id=999999` (a non-existent id). Expect the normal empty Add Book form (no banner, no error). Saving creates a plain book and touches no request.

- [ ] **Step 6: Commit**

```bash
git add app/library/routes.py app/library/templates/library/add_book.html
git commit -m "feat(requests): approve a request by prefilling the add-book form"
```

---

## Self-Review Notes

- **Spec coverage:** model (Task 1), form+submit+entry point (Task 2/3), admin review list + reject (Task 4), approve→prefill→save handoff incl. mark-approved-on-save and stale/decided-request handling (Task 5). All spec sections mapped.
- **Type consistency:** model name `BookRequest`, relationships `requester`/`reviewer`, fields `title`/`author`/`link`/`status`/`requested_by_user_id`/`reviewed_at`/`reviewed_by_user_id`, route endpoints `library.request_book`, `admin.book_requests`, `admin.reject_request`, and `?request_id=` param are used identically across all tasks.
- **Status values:** `"pending"`/`"approved"`/`"rejected"` used consistently in model default, queries, sort map, and template classes.
