from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField,  SubmitField
from wtforms.validators import DataRequired, Length


class EditProfileForm(FlaskForm):
    """
    Klasa formularza do edycji profilu użytkownika.
    """
    username = StringField('Username', validators=[DataRequired()])
    about_me = TextAreaField('About me', validators=[Length(min=0, max=140)])
    submit = SubmitField('Submit')
