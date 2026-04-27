from flask import Blueprint

from app.auth.decorators import admin_required, login_required  # noqa: F401

bp = Blueprint("auth", __name__, template_folder="templates")

from app.auth import routes  # noqa: E402, F401
