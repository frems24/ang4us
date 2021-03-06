from datetime import datetime
from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_required
from app import db
from app.main.forms import EditProfileForm, AddFisheryForm
from app.models import User, Fishery
from app.main import bp


@bp.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@bp.route('/')
@bp.route('/index')
@login_required
def index():
    posts = [
        {
            'author': {'username': 'John'},
            'body': 'Beautiful day in Portland!'
        },
        {
            'author': {'username': 'Susan'},
            'body': 'I caught a big salmon yesterday'
        }
    ]
    return render_template('index.html', title='Home Page', posts=posts)


@bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = [
        {'author': user, 'body': 'Test post #1'},
        {'author': user, 'body': 'Test post #2'}
    ]

    return render_template('user.html', user=user, posts=posts)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me

    return render_template('edit_profile.html', title='Edit Profile', form=form)


@bp.route('/fisheries')
@login_required
def get_all_fisheries():
    fisheries = Fishery.query.all()

    return render_template('fisheries.html', title='Fisheries', fisheries=fisheries)


@bp.route('/add_fishery', methods=['GET', 'POST'])
@login_required
def add_fishery():
    form = AddFisheryForm()
    if form.validate_on_submit():
        fishery = Fishery(reservoir_name=form.reservoir_name.data)
        fishery.country = form.country.data
        fishery.country = form.country.data
        fishery.place = form.place.data
        fishery.longitude = form.longitude.data
        fishery.latitude = form.latitude.data
        db.session.add(fishery)
        db.session.commit()
        flash('New fishery has been added.')
        return redirect(url_for('main.user', username=current_user.username))

    return render_template('add_fishery.html', title='Add Fishery', form=form)
