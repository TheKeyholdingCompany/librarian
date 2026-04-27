from functools import wraps

from flask import (
    Blueprint,
    abort,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.extensions import db
from app.models import Item

bp = Blueprint("main", __name__)


# Mock user "database" — hardcoded for learning purposes.
# In a real app, this would be a SQLAlchemy User model with hashed passwords.
USERS = {
    "borrower": {"password": "borrower", "role": "borrower"},
    "admin": {"password": "admin", "role": "admin"},
}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("main.login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("main.login"))
        if session.get("role") != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@bp.route("/")
@login_required
def index():
    items = db.session.scalars(db.select(Item).order_by(Item.created_at.desc())).all()
    return render_template("index.html", items=items)


@bp.route("/health")
def health():
    db.session.execute(db.text("SELECT 1"))
    return {"status": "ok"}


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = USERS.get(username)
        if user is not None and user["password"] == password:
            session["username"] = username
            session["role"] = user["role"]
            return redirect(url_for("main.index"))
        error = "Invalid username or password."
    return render_template("login.html", error=error)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("main.login"))


@bp.route("/admin")
@admin_required
def admin():
    return render_template("admin.html")
