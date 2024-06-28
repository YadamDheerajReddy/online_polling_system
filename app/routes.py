from flask import Blueprint, render_template, url_for, flash, redirect, request, abort
from app import db, bcrypt
from app.forms import RegistrationForm, LoginForm, PollForm
from app.models import User, Poll, Vote
from flask_login import login_user, current_user, logout_user, login_required

main = Blueprint('main', __name__)

@main.route('/')
@main.route('/home')
def home():
    polls = Poll.query.all()
    return render_template('index.html', polls=polls)

@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Register', form=form)

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@main.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.home'))

@main.route('/create_poll', methods=['GET', 'POST'])
@login_required
def create_poll():
    form = PollForm()
    if form.validate_on_submit():
        options = form.options.data.split(',')
        options = [option.strip() for option in options]
        poll = Poll(question=form.question.data, options=','.join(options), author=current_user)
        db.session.add(poll)
        db.session.commit()
        flash('Your poll has been created!', 'success')
        return redirect(url_for('main.home'))
    return render_template('create_poll.html', title='Create Poll', form=form)

@main.route('/poll/<int:poll_id>', methods=['GET', 'POST'])
@login_required
def poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    if not poll.active:
        flash('This poll has been closed.', 'info')
        return redirect(url_for('main.results', poll_id=poll.id))

    if request.method == 'POST':
        selected_option = request.form.get('option')
        vote = Vote(poll_id=poll.id, option=selected_option, user_id=current_user.id)
        db.session.add(vote)
        db.session.commit()
        flash('Your vote has been recorded!', 'success')
        return redirect(url_for('main.results', poll_id=poll.id))
    
    options = poll.options.split(',')
    return render_template('poll.html', title=poll.question, poll=poll, options=options)

@main.route('/results/<int:poll_id>')
@login_required
def results(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    votes = Vote.query.filter_by(poll_id=poll.id).all()
    results = {}
    for vote in votes:
        results[vote.option] = results.get(vote.option, 0) + 1
    return render_template('results.html', title='Results', poll=poll, results=results)

@main.route('/stop_poll/<int:poll_id>')
@login_required
def stop_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    if poll.author != current_user:
        flash('You are not authorized to stop this poll', 'danger')
        return redirect(url_for('main.home'))
    poll.active = False
    db.session.commit()
    flash('The poll has been stopped', 'info')
    return redirect(url_for('main.results', poll_id=poll.id))

@main.route('/delete_poll/<int:poll_id>', methods=['POST'])
@login_required
def delete_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    if poll.author != current_user:
        abort(403)
    db.session.delete(poll)
    db.session.commit()
    flash('The poll has been deleted', 'success')
    return redirect(url_for('main.home'))
