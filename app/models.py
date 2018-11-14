from datetime import datetime, timedelta
import base64
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask import url_for
from flask_login import UserMixin
from app import login, db
from app.apihelper import PaginatedApiMixin, ApiBaseModel


users_fisheries = db.Table('users_fisheries',
                           db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                           db.Column('fishery_id', db.Integer, db.ForeignKey('fishery.id'))
                           )


class User(PaginatedApiMixin, UserMixin, ApiBaseModel):
    """ 'user' table in database
        class UserMixin adds: is_authenticated, is_active, is_anonymous, get_id()
    """
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    email_confirmed = db.Column(db.Boolean)                         # dopisać obsługę
    password_hash = db.Column(db.String(128))
    token = db.Column(db.String(32), index=True, unique=True)
    token_expiration = db.Column(db.DateTime)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)     # to nie działa dla api
    about_me = db.Column(db.String(140))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    fisheries = db.relationship('Fishery', backref='author', lazy='dynamic')

    _default_fields = [
        'username',
        'last_seen',
        'about_me',
        'joined_recently',
        'links'
    ]
    _hidden_fields = [
        'password_hash',
        'token',
        'token_expiration'
    ]
    _readonly_fields = [
        'email_confirmed',
        'modified_at'
    ]

    def __repr__(self):
        return f'<User {self.username}>'

    @property
    def joined_recently(self):
        return self.created_at > datetime.utcnow() - timedelta(days=3)

    @property
    def links(self):
        return {'self': url_for('api.get_user', id=self.id)}

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def create_user(self, **kwargs):
        password = kwargs.pop('password')
        self.from_dict(**kwargs)
        self.set_password(password)

    def get_token(self, expires_in=3600):
        now = datetime.utcnow()
        if self.token and self.token_expiration > now + timedelta(seconds=60):
            return self.token
        self.token = base64.b64encode(os.urandom(24)).decode('utf-8')
        self.token_expiration = now + timedelta(seconds=expires_in)
        db.session.add(self)
        return self.token

    def revoke_token(self):
        self.token_expiration = datetime.utcnow() - timedelta(seconds=1)

    @staticmethod
    def check_token(token):
        user = User.query.filter_by(token=token).first()
        if user is None or user.token_expiration < datetime.utcnow():
            return None

        return user


class Post(db.Model):
    """ 'post' table in database """
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime)
    body = db.Column(db.String(140))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    _default_fields = {
        'body'
    }

    def __repr__(self):
        return f'<Post {self.body}>'


class Fishery(PaginatedApiMixin, ApiBaseModel):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime)
    reservoir_name = db.Column(db.String(40), index=True)
    country = db.Column(db.String(40), index=True)
    place = db.Column(db.String(140))
    longitude = db.Column(db.Float)
    latitude = db.Column(db.Float)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    _default_fields = {
        'reservoir_name',
        'country',
        'place',
        'longitude',
        'latitude'
    }
    _hidden_fields = {}
    _readonly_fields = {}

    def __repr__(self):
        return f'<Fishery {self.reservoir_name}>'

    @property
    def links(self):
        return {'self': url_for('api.get_fishery', id=self.id)}


class Fish(PaginatedApiMixin, ApiBaseModel):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime)
    species = db.Column(db.String(40), index=True, unique=True)
    description = db.Column(db.String(140))
    photos = db.Column(db.String(80))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    _default_fields = {
        'species',
        'description',
        'photos'
    }

    _hidden_fields = {}
    _readonly_fields = {}


@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
