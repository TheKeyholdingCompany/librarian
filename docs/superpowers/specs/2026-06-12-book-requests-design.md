# Book Requests — Design

## Summary

Let any logged-in user request a new book for the library by submitting a
**title**, **author**, and **link**. Requests land in a pending queue that
admins review. Approving a request takes the admin to the existing Add Book
form, pre-filled from the request; saving the book marks the request approved.
Rejecting marks it rejected. Decisions are recorded (who/when).

## Code layout

- Submit route + form: **`library`** blueprint.
- Review page + reject route: **`admin`** blueprint.
- Approve reuses the existing **`library.add_book`** route (already
  `@admin_required`) via a `?request_id=N` query param — no new approve route.

## Data model — `BookRequest` (`app/models.py`)

| Column                 | Type               | Notes                                  |
|------------------------|--------------------|----------------------------------------|
| `id`                   | Integer PK         |                                        |
| `title`                | String(120)        | required                               |
| `author`               | String(120)        | required                               |
| `link`                 | String(500)        | required; URL to the book              |
| `requested_by_user_id` | FK `users.id`      | required                               |
| `status`               | String(20)         | default `"pending"`; `pending`/`approved`/`rejected` |
| `created_at`           | DateTime(tz)       | default now (UTC)                      |
| `reviewed_at`          | DateTime(tz)       | nullable                               |
| `reviewed_by_user_id`  | FK `users.id`      | nullable                               |

Relationships:
- `requester` → `User` (the submitter), via `requested_by_user_id`.
- `reviewer` → `User` (the deciding admin), via `reviewed_by_user_id`.

Both FKs reference `users.id`; specify explicit `foreign_keys=` on the
relationships to disambiguate.

A new Alembic migration adds the `book_requests` table. Follows the existing
`Rating`/`Borrow` shape (FKs + tz-aware `created_at`).

## Form & submit flow (library blueprint)

**`RequestBookForm`** in `app/forms.py`:
- `title` — `StringField`, `DataRequired`, `Length(max=120)`
- `author` — `StringField`, `DataRequired`, `Length(max=120)`
- `link` — `StringField`, `DataRequired`, `URL`, `Length(max=500)`
- `submit` — `SubmitField`

**`GET/POST /request`** → `request_book()` (`@login_required`):
- GET: render `library/request_book.html`.
- POST (valid): create `BookRequest(requested_by_user_id=session["user_id"],
  status="pending", …)`, commit, flash success, redirect to `library.index`.

**Entry point**: a "Request a book" link/button on `library/index.html`.

## Admin review flow (admin blueprint)

**`GET /admin/requests`** → `book_requests()` (`@admin_required`):
- List requests, pending first, then by `created_at` desc.
- Each row: title, author, clickable link, requester username, date, status.
- Pending rows show **Approve** (link to `library.add_book?request_id=<id>`)
  and **Reject** (POST form).

**`POST /admin/requests/<int:request_id>/reject`** → `reject_request()`
(`@admin_required`):
- Load request; if not `pending`, flash info and no-op.
- Else set `status="rejected"`, `reviewed_at=now`,
  `reviewed_by_user_id=session["user_id"]`, commit, flash, redirect back.

**Entry point**: a "Review book requests" link on `admin/dashboard.html`,
with a pending-count badge.

## Approve → prefill → save handoff (`library.add_book`)

Extend the existing `add_book` route:

- **GET with `?request_id=N`**: load the request. If it exists and is pending,
  prefill `form.name = title` and
  `form.description = "By {author}\n{link}"`. Render a banner: "Creating book
  from a request by {requester}." The form's `action` preserves `request_id`
  in the query string so the POST carries it.
- **POST with `request_id=N`**: after creating and committing the `Book`,
  load the request; if it exists and is pending, set `status="approved"`,
  `reviewed_at=now`, `reviewed_by_user_id=session["user_id"]` and commit.

A request is only marked approved once the book is actually saved — abandoning
the form leaves the request pending.

## Error handling & edge cases

- `request_id` referencing a missing or already-decided request → ignore
  prefill/marking; behave as a normal Add Book (optional info flash). No hard
  failure.
- Reject on a non-pending request → info flash, no-op.
- Standard WTForms validation + CSRF (inherited from `FlaskForm`, as used
  elsewhere).

## Testing

The repo has no automated test framework wired up (only `test_db.py`), so
verification is manual:

1. As a borrower, submit a request → confirm it appears pending in
   `/admin/requests`.
2. As admin, Approve → confirm Add Book form is prefilled, save the book →
   confirm the book exists and the request status flips to `approved` with
   reviewer recorded.
3. As admin, Reject another request → confirm status flips to `rejected`.
4. Abandon an approve (don't save) → confirm request stays `pending`.
