from flask import Blueprint

bp = Blueprint("about", __name__, template_folder="templates")

from app.about import routes  # noqa: E402, F401
