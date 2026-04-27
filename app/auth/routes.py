from flask import redirect, render_template, request, session, url_for

from app.auth import bp

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
        user = USERS.get(username)
        if user is not None and user["password"] == password:
            session["username"] = username
            session["role"] = user["role"]
            return redirect(url_for("library.index"))
        error = "Invalid username or password."
    return render_template("auth/login.html", error=error)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
