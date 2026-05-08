from datetime import datetime, timezone

from app.extensions import db

favorites = db.Table(
    "favorites",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("book_id", db.Integer, db.ForeignKey("books.id"), primary_key=True),
)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    # Stable Keycloak `sub` claim — the only identifier guaranteed not to
    # change on email/username edits in the IdP. Nullable to allow the
    # existing seeded admin row to be linked by email on first OIDC login.
    keycloak_sub = db.Column(db.String(64), unique=True, nullable=True, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # Nullable since Keycloak owns credentials. Kept around so the column can
    # be dropped in a follow-up migration once nothing references it.
    password_hash = db.Column(db.String(200), nullable=True)
    role = db.Column(db.String(20), default="borrower", nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship to borrows
    borrows = db.relationship("Borrow", backref="user", lazy=True, cascade="all, delete-orphan")
    # Relationship to favourite books
    favorites = db.relationship(
        "Book",
        secondary=favorites,
        lazy="subquery",
        backref=db.backref("favorited_by", lazy="subquery"),
    )
    # Relationship to ratings
    ratings = db.relationship("Rating", back_populates="user", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.id} {self.username!r}>"


class Item(db.Model):
    __tablename__ = "items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self):
        return f"<Item {self.id} {self.name!r}>"


class Book(db.Model):
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    photo_filename = db.Column(db.String(200), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship to borrows
    borrows = db.relationship("Borrow", backref="book", lazy=True, cascade="all, delete-orphan")
    # Relationship to ratings
    ratings = db.relationship("Rating", back_populates="book", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Book {self.id} {self.name!r}>"


class Borrow(db.Model):
    __tablename__ = "borrows"

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    borrowed_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    due_date = db.Column(db.DateTime(timezone=True), nullable=True)
    returned_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Borrow {self.id} book_id={self.book_id} user_id={self.user_id}>"

    @property
    def is_active(self):
        """Check if the book is currently borrowed (not returned)."""
        return self.returned_at is None


class Rating(db.Model):
    __tablename__ = "ratings"

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    review = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    book = db.relationship("Book", back_populates="ratings")
    user = db.relationship("User", back_populates="ratings")

    def __repr__(self):
        return f"<Rating {self.id} book_id={self.book_id} user_id={self.user_id} rating={self.rating}>"

    __table_args__ = (db.UniqueConstraint('book_id', 'user_id', name='unique_user_book_rating'),)
