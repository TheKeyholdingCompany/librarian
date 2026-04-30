from flask import render_template, redirect, url_for, session, flash
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import selectinload
from werkzeug.security import generate_password_hash

from app.auth.decorators import login_required, admin_required
from app.extensions import db
from app.forms import BookForm
from app.library import bp
from app.models import Book, Borrow, User


@bp.route("/")
@login_required
def index():
    books = db.session.scalars(db.select(Book).order_by(Book.created_at.desc())).all()
    
    # Get borrow status for each book
    book_status = {}
    for book in books:
        active_borrow = db.session.scalars(
            db.select(Borrow).where(
                (Borrow.book_id == book.id) & (Borrow.returned_at == None)
            )
        ).first()
        book_status[book.id] = active_borrow
    
    return render_template("library/index.html", books=books, book_status=book_status)


@bp.route("/health")
def health():
    db.session.execute(db.text("SELECT 1"))
    return {"status": "ok"}


@bp.route("/dashboard")
@login_required
def dashboard():
    username = session.get("username")
    user = db.session.scalars(
        db.select(User)
        .options(selectinload(User.borrows).selectinload(Borrow.book))
        .where(User.username == username)
    ).first()

    borrows = []
    if user:
        borrows = sorted(user.borrows, key=lambda borrow: borrow.borrowed_at or datetime.min, reverse=True)

    return render_template("library/dashboard.html", user=user, borrows=borrows)



@bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_book():
    form = BookForm()
    if form.validate_on_submit():
        book = Book(name=form.name.data, description=form.description.data)
        db.session.add(book)
        db.session.commit()
        return redirect(url_for("library.index"))
    return render_template("library/add_book.html", form=form)


@bp.route("/<int:book_id>/borrow", methods=["POST"])
@login_required
def borrow_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        flash("Book not found.", "error")
        return redirect(url_for("library.index"))
    
    # Get or create user from session username
    username = session.get("username")
    if not username:
        flash("You must be logged in to borrow a book.", "error")
        return redirect(url_for("auth.login"))
    
    # Try to find user, create if doesn't exist
    user = db.session.scalars(db.select(User).where(User.username == username)).first()
    if not user:
        # Create new user with default email based on username
        user = User(
            username=username,
            email=f"{username}@library.local",
            password_hash=generate_password_hash(username),
            role="borrower",
        )
        db.session.add(user)
        db.session.commit()
    
    # Check if book is already borrowed
    active_borrow = db.session.scalars(
        db.select(Borrow).where(
            (Borrow.book_id == book_id) & (Borrow.returned_at == None)
        )
    ).first()
    
    if active_borrow:
        flash(f"This book is already borrowed by {active_borrow.user.username}.", "info")
        return redirect(url_for("library.index"))
    
    # Create borrow record
    borrow = Borrow(book_id=book_id, user_id=user.id)
    borrow.due_date = datetime.now(timezone.utc) + timedelta(weeks=2)
    db.session.add(borrow)
    db.session.commit()
    
    flash(f"You've borrowed '{book.name}'! Due back on {borrow.due_date.strftime('%B %d, %Y')}.", "success")
    return redirect(url_for("library.index"))


@bp.route("/<int:book_id>/return", methods=["POST"])
@login_required
def return_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        flash("Book not found.", "error")
        return redirect(url_for("library.index"))
    
    # Get the active borrow
    active_borrow = db.session.scalars(
        db.select(Borrow).where(
            (Borrow.book_id == book_id) & (Borrow.returned_at == None)
        )
    ).first()
    
    if not active_borrow:
        flash("This book is not currently borrowed.", "error")
        return redirect(url_for("library.index"))
    
    # Get current user
    username = session.get("username")
    current_user = db.session.scalars(db.select(User).where(User.username == username)).first()
    
    # Check if user is allowed to return this book
    is_owner = current_user and current_user.id == active_borrow.user_id
    is_admin = session.get("role") == "admin"
    
    if not (is_owner or is_admin):
        flash("You don't have permission to return this book.", "error")
        return redirect(url_for("library.index"))
    
    # Mark as returned
    active_borrow.returned_at = datetime.now(timezone.utc)
    db.session.commit()
    
    flash(f"You've returned '{book.name}'!", "success")
    return redirect(url_for("library.index"))


@bp.route("/<int:book_id>/delete", methods=["POST"])
@login_required
def delete_book(book_id):
    # Check if user is admin
    if session.get("role") != "admin":
        flash("You don't have permission to delete books.", "error")
        return redirect(url_for("library.index"))
    
    book = db.session.get(Book, book_id)
    if not book:
        flash("Book not found.", "error")
        return redirect(url_for("library.index"))
    
    book_name = book.name
    
    # Delete associated borrow records first
    db.session.query(Borrow).filter(Borrow.book_id == book_id).delete()
    
    # Delete the book
    db.session.delete(book)
    db.session.commit()
    
    flash(f"'{book_name}' has been deleted.", "success")
    return redirect(url_for("library.index"))