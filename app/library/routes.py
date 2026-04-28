from flask import render_template

from app.auth import login_required
from app.extensions import db
from app.library import bp
from app.models import Book


@bp.route("/")
@login_required
def index():
    books = db.session.scalars(db.select(Book).order_by(Book.created_at.desc())).all()
    return render_template("library/index.html", books=books)


@bp.route("/health")
def health():
    db.session.execute(db.text("SELECT 1"))
    return {"status": "ok"}
