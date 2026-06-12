from datetime import datetime, timezone

from flask import flash, redirect, render_template, session, url_for
from sqlalchemy.orm import selectinload

from app.admin import bp
from app.auth import admin_required
from app.extensions import db
from app.models import Borrow, User, BookRequest


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


@bp.route("/admin/borrowers")
@admin_required
def borrowers():
    users = User.query.options(
        selectinload(User.borrows).selectinload(Borrow.book)
    ).order_by(User.created_at.desc()).all()
    return render_template("admin/borrowers.html", users=users)


@bp.route("/admin/users")
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)


@bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    # Self-protect: an admin shouldn't be able to wipe their own row out from
    # under their session. Disabling in Keycloak is the right escape hatch.
    if user.id == session.get("user_id"):
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("admin.users"))

    db.session.delete(user)
    db.session.commit()
    flash(f"Local mirror row for '{user.username}' deleted. Disable in Keycloak to block sign-in.", "success")
    return redirect(url_for("admin.users"))


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
