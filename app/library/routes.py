from flask import render_template, redirect, url_for

from app.auth import login_required
from app.extensions import db
from app.forms import BookForm
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



@bp.route("/add", methods=["GET", "POST"])
@login_required
def add_book():
    form = BookForm()
    if form.validate_on_submit():
        book = Book(name=form.name.data, description=form.description.data)
        db.session.add(book)
        db.session.commit()
        return redirect(url_for("library.index"))
    return render_template("library/add_book.html", form=form)