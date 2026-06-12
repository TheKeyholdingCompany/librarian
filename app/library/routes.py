from flask import render_template, redirect, url_for, session, flash, request, jsonify
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from app.auth.decorators import login_required, admin_required
from app.extensions import db
from app.forms import BookForm, RequestBookForm
from app.library import bp
from app.models import Book, Borrow, User, Rating, BookRequest
from app.storage import presign_put, UnsupportedImageType, ALLOWED_IMAGE_TYPES


@bp.route("/")
@login_required
def index():
    search_query = request.args.get("q", "").strip()
    book_stmt = db.select(Book)
    if search_query:
        book_stmt = book_stmt.where(
            or_(
                Book.name.ilike(f"%{search_query}%"),
                Book.description.ilike(f"%{search_query}%"),
            )
        )
    books = db.session.scalars(book_stmt.order_by(Book.created_at.desc())).all()
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
        search_query=search_query,
    )


@bp.route("/request", methods=["GET", "POST"])
@login_required
def request_book():
    form = RequestBookForm()
    if form.validate_on_submit():
        book_request = BookRequest(
            title=form.title.data,
            author=form.author.data,
            link=form.link.data,
            requested_by_user_id=session.get("user_id"),
            status="pending",
        )
        db.session.add(book_request)
        db.session.commit()
        flash("Thanks! Your book request has been submitted for review.", "success")
        return redirect(url_for("library.index"))
    return render_template("library/request_book.html", form=form)


@bp.route("/<int:book_id>/favorite", methods=["POST"])
@login_required
def favorite_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        flash("Book not found.", "error")
        return redirect(url_for("library.index"))

    user = db.session.get(User, session.get("user_id"))
    if not user:
        flash("You must be logged in to favourite a book.", "error")
        return redirect(url_for("auth.login"))

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
    db.session.execute(db.text("SELECT 1"))
    return {"status": "ok"}


@bp.route("/dashboard")
@login_required
def dashboard():
    username = session.get("username")
    user = db.session.scalars(
        db.select(User)
        .options(
            selectinload(User.borrows).selectinload(Borrow.book),
            selectinload(User.favorites),
        )
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
        .options(
            selectinload(User.borrows).selectinload(Borrow.book),
            selectinload(User.favorites),
        )
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
    # When reached via an admin "Approve" link the URL carries ?request_id=N.
    # The form has no explicit action, so it posts back to this same URL with
    # the query string intact — request_id survives the GET→POST round trip.
    request_id = request.args.get("request_id", type=int)
    book_request = db.session.get(BookRequest, request_id) if request_id else None
    # Only honour a request that still exists and hasn't been decided yet.
    if book_request and book_request.status != "pending":
        book_request = None

    form = BookForm()
    form.submit.label.text = "Add Book"
    if form.validate_on_submit():
        book = Book(
            name=form.name.data,
            description=form.description.data,
            photo_filename=form.photo_key.data or None,
        )
        db.session.add(book)
        # Flip the request to approved only once the book is actually saved;
        # abandoning this form leaves it pending. The UPDATE is guarded on
        # status == "pending" so the transition is atomic at the DB level: if
        # another admin decided this request between page load and submit, the
        # WHERE matches no rows and we don't clobber their decision (the book is
        # still saved either way).
        if book_request:
            db.session.execute(
                db.update(BookRequest)
                .where(BookRequest.id == book_request.id, BookRequest.status == "pending")
                .values(
                    status="approved",
                    reviewed_at=datetime.now(timezone.utc),
                    reviewed_by_user_id=session.get("user_id"),
                )
            )
        db.session.commit()
        flash(f"Book '{book.name}' added successfully!", "success")
        return redirect(url_for("library.index"))

    # Prefill from the request on first render only — don't clobber what the
    # admin typed if validation bounced the POST back.
    if book_request and request.method == "GET":
        form.name.data = book_request.title
        form.description.data = f"By {book_request.author}\n{book_request.link}"

    return render_template(
        "library/add_book.html",
        form=form,
        form_title="Add a New Book",
        allowed_extensions=sorted(ALLOWED_IMAGE_TYPES.keys()),
        book_request=book_request,
    )


@bp.route("/<int:book_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        flash("Book not found.", "error")
        return redirect(url_for("library.index"))

    # BookForm.photo_key is a HiddenField; obj=book preloads name/description
    # but leaves photo_key empty so the form only overwrites the cover when
    # the admin actually picks a new file.
    form = BookForm(obj=book)
    form.submit.label.text = "Save Changes"

    if form.validate_on_submit():
        book.name = form.name.data
        book.description = form.description.data
        if form.photo_key.data:
            book.photo_filename = form.photo_key.data
        db.session.commit()
        flash(f"Book '{book.name}' updated successfully!", "success")
        return redirect(url_for("library.index"))

    return render_template(
        "library/add_book.html",
        form=form,
        book=book,
        form_title="Edit Book",
        allowed_extensions=sorted(ALLOWED_IMAGE_TYPES.keys()),
    )


@bp.route("/photo-upload-url")
@admin_required
def photo_upload_url():
    """Mint a short-lived presigned PUT URL for the add/edit book form's JS.

    The browser sends ?ext=jpg, gets back {url, key, content_type}, PUTs the
    file directly to S3, then submits the form with `key` as a hidden field.
    The Flask process never sees the bytes.
    """
    ext = request.args.get("ext", "")
    try:
        return jsonify(presign_put(ext))
    except UnsupportedImageType:
        return jsonify({"error": f"Unsupported file type: {ext!r}"}), 400


@bp.route("/<int:book_id>/borrow", methods=["POST"])
@login_required
def borrow_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        flash("Book not found.", "error")
        return redirect(url_for("library.index"))
    
    user = db.session.get(User, session.get("user_id"))
    if not user:
        flash("You must be logged in to borrow a book.", "error")
        return redirect(url_for("auth.login"))

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