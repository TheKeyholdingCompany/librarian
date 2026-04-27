from functools import wraps

from flask import abort, redirect, session, url_for


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("auth.login"))
        if session.get("role") != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped
