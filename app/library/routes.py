from flask import render_template

from app.auth import login_required
from app.extensions import db
from app.library import bp
from app.models import Item


@bp.route("/")
@login_required
def index():
    items = db.session.scalars(db.select(Item).order_by(Item.created_at.desc())).all()
    return render_template("library/index.html", items=items)


@bp.route("/health")
def health():
    db.session.execute(db.text("SELECT 1"))
    return {"status": "ok"}
