from flask import abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from app.admin import bp
from app.auth import admin_required
from app.extensions import db
from app.models import User


@bp.route("/admin")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html")


@bp.route("/admin/users")
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)


@bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Prevent admin from deleting themselves
    if user.id == session.get("user_id"):
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("admin.users"))
    
    db.session.delete(user)
    db.session.commit()
    flash(f"User '{user.username}' has been deleted.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/admin/users/<int:user_id>/reset-password", methods=["POST"])
@admin_required
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get("new_password", "")
    
    if not new_password or len(new_password) < 6:
        flash("Password must be at least 6 characters.", "error")
        return redirect(url_for("admin.users"))
    
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    flash(f"Password for '{user.username}' has been reset.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/admin/users/<int:user_id>/change-role", methods=["POST"])
@admin_required
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get("role", "borrower")
    
    if new_role not in ["borrower", "admin"]:
        flash("Invalid role.", "error")
        return redirect(url_for("admin.users"))
    
    # Prevent admin from changing their own role
    if user.id == session.get("user_id"):
        flash("You cannot change your own role.", "error")
        return redirect(url_for("admin.users"))
    
    user.role = new_role
    db.session.commit()
    flash(f"Role for '{user.username}' changed to '{new_role}'.", "success")
    return redirect(url_for("admin.users"))
