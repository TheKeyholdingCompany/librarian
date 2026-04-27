from flask import Blueprint, render_template

from app.extensions import db
from app.models import Item

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    items = db.session.scalars(db.select(Item).order_by(Item.created_at.desc())).all()
    return render_template("index.html", items=items)


@bp.route("/health")
def health():
    db.session.execute(db.text("SELECT 1"))
    return {"status": "ok"}
