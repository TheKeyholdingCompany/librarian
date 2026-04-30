from flask import render_template, redirect, url_for, session, flash, request
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import selectinload
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import os
from uuid import uuid4

from app.auth.decorators import login_required, admin_required
from app.extensions import db
from app.forms import BookForm
from app.library import bp
from app.models import Book, Borrow, User, Rating

# Photo upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def _get_or_create_user(username):
    if not username:
        return None

    user = db.session.scalar(db.select(User).where(User.username == username))
    if not user:
        user = User(
            username=username,
            email=f"{username}@library.local",
            role=session.get("role", "borrower"),
        )
        db.session.add(user)
        db.session.commit()
    return user


@bp.route("/")
@login_required
def index():
    books = db.session.scalars(db.select(Book).order_by(Book.created_at.desc())).all()
    username = session.get("username")
    favorite_book_ids = set()
    if username:
        user = db.session.scalar(db.select(User).where(User.username == username))
        if user:
            favorite_book_ids = {book.id for book in user.favorites}

    # Get borrow status for each book
    book_status = {}
    book_ratings = {}
    user_rating_data = {}
    user_id = session.get("user_id")
    
    for book in books:
        # Borrow status
        active_borrow = db.session.scalars(
            db.select(Borrow).where(
                (Borrow.book_id == book.id) & (Borrow.returned_at == None)
            )
        ).first()
        book_status[book.id] = active_borrow
        
        # Initialize user rating data
        user_rating_data[book.id] = None
        
        # Ratings
        ratings = db.session.scalars(
            db.select(Rating).where(Rating.book_id == book.id)
        ).all()
        if ratings:
            avg_rating = sum(r.rating for r in ratings) / len(ratings)
            book_ratings[book.id] = round(avg_rating, 1)
        else:
            book_ratings[book.id] = None
            
        # User's rating
        if user_id:
            user_rating = db.session.scalars(
                db.select(Rating).where(
                    (Rating.book_id == book.id) & (Rating.user_id == user_id)
                )
            ).first()
            user_rating_data[book.id] = {
                "rating": user_rating.rating,
                "review": user_rating.review,
            } if user_rating else None
    
    return render_template(
        "library/index.html",
        books=books,
        book_status=book_status,
        favorite_book_ids=favorite_book_ids,
        book_ratings=book_ratings,
        user_rating_data=user_rating_data,
    )


@bp.route("/<int:book_id>/favorite", methods=["POST"])
@login_required
def favorite_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        flash("Book not found.", "error")
        return redirect(url_for("library.index"))

    username = session.get("username")
    if not username:
        flash("You must be logged in to favourite a book.", "error")
        return redirect(url_for("auth.login"))

    user = _get_or_create_user(username)
    if not user:
        flash("Unable to find or create user.", "error")
        return redirect(url_for("library.index"))

    if book in user.favorites:
        user.favorites.remove(book)
        flash(f"Removed '{book.name}' from your favourites.", "success")
    else:
        user.favorites.append(book)
        flash(f"Added '{book.name}' to your favourites.", "success")

    db.session.commit()
    return redirect(url_for("library.index"))


@bp.route("/rate/<int:book_id>", methods=["POST"])
@login_required
def rate_book(book_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in to rate books.", "error")
        return redirect(url_for("library.index"))
    
    rating_value = request.form.get("rating", type=int)
    review_text = request.form.get("review", "").strip()
    
    if not rating_value or rating_value < 1 or rating_value > 5:
        flash("Please provide a valid rating (1-5 stars).", "error")
        return redirect(url_for("library.index"))
    
    # Check if user already rated this book
    existing_rating = db.session.scalars(
        db.select(Rating).where(
            (Rating.book_id == book_id) & (Rating.user_id == user_id)
        )
    ).first()
    
    if existing_rating:
        # Update existing rating
        existing_rating.rating = rating_value
        existing_rating.review = review_text if review_text else None
        existing_rating.updated_at = datetime.now(timezone.utc)
        flash("Your rating has been updated.", "success")
    else:
        # Create new rating
        new_rating = Rating(
            book_id=book_id,
            user_id=user_id,
            rating=rating_value,
            review=review_text if review_text else None
        )
        db.session.add(new_rating)
        flash("Thank you for rating this book!", "success")
    
    db.session.commit()
    return redirect(url_for("library.index"))


@bp.route("/health")
def health():


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


@bp.route("/dashboard/<int:user_id>")
@login_required
def view_borrower_dashboard(user_id):
    # Allow viewing own dashboard or if user is admin
    current_username = session.get("username")
    current_user = db.session.scalars(
        db.select(User).where(User.username == current_username)
    ).first()
    
    is_admin = session.get("role") == "admin"
    target_user = db.session.scalars(
        db.select(User)
        .options(selectinload(User.borrows).selectinload(Borrow.book))
        .where(User.id == user_id)
    ).first()
    
    if not target_user:
        flash("User not found.", "error")
        return redirect(url_for("library.index"))
    
    # Allow access if viewing own dashboard or if admin
    is_owner = current_user and current_user.id == target_user.id
    if not (is_owner or is_admin):
        flash("You don't have permission to view this dashboard.", "error")
        return redirect(url_for("library.index"))
    
    borrows = sorted(target_user.borrows, key=lambda borrow: borrow.borrowed_at or datetime.min, reverse=True)
    return render_template("library/dashboard.html", user=target_user, borrows=borrows)


@bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_book():
    form = BookForm()
    if form.validate_on_submit():
        book = Book(name=form.name.data, description=form.description.data)
        
        # Handle file upload
        if form.photo.data:
            file = form.photo.data
            filename = secure_filename(file.filename)
            # Add unique prefix to avoid name collisions
            filename = f"{uuid4().hex}_{filename}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            book.photo_filename = filename
        
        db.session.add(book)
        db.session.commit()
        flash(f"Book '{book.name}' added successfully!", "success")
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