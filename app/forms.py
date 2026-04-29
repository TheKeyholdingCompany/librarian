from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length


class BookForm(FlaskForm):
    name = StringField("Book Name", validators=[DataRequired(), Length(min=1, max=120)])
    description = TextAreaField("Description", validators=[Length(max=500)])
    submit = SubmitField("Add Book")
