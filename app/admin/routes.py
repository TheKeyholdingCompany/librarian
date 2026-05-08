from flask import flash, redirect, render_template, session, url_for
from sqlalchemy.orm import selectinload

from app.admin import bp
from app.auth import admin_required
from app.extensions import db
from app.models import Borrow, User


@bp.route("/admin")
@admin_required
def dashboard():
    username = session.get("username")
    user = db.session.scalar(
        db.select(User)
        .options(selectinload(User.favorites))
        .where(User.username == username)
    )
    return render_template("admin/dashboard.html", user=user)


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
