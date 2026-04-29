from flask import render_template, redirect, url_for, flash, session
from datetime import datetime, timezone, timedelta

from app.auth import login_required
from app.extensions import db
from app.borrower import bp
from app.models import Borrow, Book


@bp.route("/dashboard")
@login_required
def dashboard():
    """Borrower dashboard showing borrow history, current borrows, and due soon alerts."""
    username = session.get("username")
    user_id = session.get("user_id")
    
    # Get current borrows (not returned)
    current_borrows = db.session.scalars(
        db.select(Borrow).where(
            (Borrow.user_id == user_id) & (Borrow.returned_at == None)
        ).order_by(Borrow.due_date.asc())
    ).all()
    
    # Get borrow history (returned books)
    borrow_history = db.session.scalars(
        db.select(Borrow).where(
            (Borrow.user_id == user_id) & (Borrow.returned_at != None)
        ).order_by(Borrow.returned_at.desc())
    ).all()
    
    # Get due soon alerts (within 3 days)
    due_soon_date = datetime.now(timezone.utc) + timedelta(days=3)
    due_soon = [
        b for b in current_borrows 
        if b.due_date and b.due_date <= due_soon_date
    ]
    
    # Get overdue books
    overdue = [
        b for b in current_borrows 
        if b.due_date and b.due_date < datetime.now(timezone.utc)
    ]
    
    return render_template(
        "borrower/dashboard.html",
        current_borrows=current_borrows,
        borrow_history=borrow_history,
        due_soon=due_soon,
        overdue=overdue,
        username=username
    )


@bp.route("/borrow-history")
@login_required
def borrow_history():
    """View complete borrow history."""
    user_id = session.get("user_id")
    
    all_borrows = db.session.scalars(
        db.select(Borrow).where(Borrow.user_id == user_id).order_by(Borrow.borrowed_at.desc())
    ).all()
    
    return render_template("borrower/borrow_history.html", borrows=all_borrows)