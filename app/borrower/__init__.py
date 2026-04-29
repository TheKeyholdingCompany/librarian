from flask import Blueprint

bp = Blueprint("borrower", __name__, url_prefix="/borrower")

from app.borrower import routes