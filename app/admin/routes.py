from flask import render_template

from app.admin import bp
from app.auth import admin_required


@bp.route("/admin")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html")
