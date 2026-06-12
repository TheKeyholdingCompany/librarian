from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, Optional, Regexp, URL


class BookForm(FlaskForm):
    name = StringField("Book Name", validators=[DataRequired(), Length(min=1, max=120)])
    description = TextAreaField("Description", validators=[Length(max=500)])
    # photo_key holds the S3 object key (e.g. "books/<uuid>.jpg") that the
    # browser populates via JS after a presigned PUT. Pattern guards against
    # the form being submitted with a key outside the expected prefix.
    photo_key = HiddenField(
        "Photo Key",
        validators=[Optional(), Regexp(r"^books/[A-Za-z0-9._-]+$", message="Invalid photo key")],
    )
    submit = SubmitField("Add Book")


class RequestBookForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(min=1, max=120)])
    author = StringField("Author", validators=[DataRequired(), Length(min=1, max=120)])
    link = StringField(
        "Link",
        validators=[DataRequired(), URL(message="Enter a valid URL (including http:// or https://)."), Length(max=500)],
    )
    submit = SubmitField("Submit Request")
