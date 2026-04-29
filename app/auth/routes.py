from flask import redirect, render_template, request, session, url_for, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import logging

logger = logging.getLogger(__name__)

from app.auth import bp
from app.extensions import db
from app.forms import SignupForm
from app.models import User

# Mock user "database" — hardcoded for learning purposes.
# In a real app, this would be a SQLAlchemy User model with hashed passwords.
USERS = {
    "borrower": {"password": "borrower", "role": "borrower"},
    "admin": {"password": "admin", "role": "admin"},
}


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        # First check the database for real users
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            return redirect(url_for("library.index"))
        
        # Fall back to mock users for learning purposes
        mock_user = USERS.get(username)
        if mock_user is not None and mock_user["password"] == password:
            session["username"] = username
            session["role"] = mock_user["role"]
            return redirect(url_for("library.index"))
        
        error = "Invalid username or password."
    return render_template("auth/login.html", error=error)


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    form = SignupForm()
    if request.method == "POST":
        logger.info(f"POST data: {request.form}")
        logger.info(f"Form validate_on_submit: {form.validate_on_submit()}")
        logger.info(f"Form errors: {form.errors}")
    
    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip()
        password = form.password.data
        
        logger.info(f"Signup attempt: username={username}, email={email}")
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "error")
            return render_template("auth/signup.html", form=form)
        
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return render_template("auth/signup.html", form=form)
        
        # Create new user with hashed password
        try:
            new_user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                role="borrower"
            )
            db.session.add(new_user)
            db.session.commit()
            
            logger.info(f"User created successfully: id={new_user.id}, username={username}")
            
            flash("Account created! Please log in.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user: {e}")
            flash(f"Error creating account: {str(e)}", "error")
    
    return render_template("auth/signup.html", form=form)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
