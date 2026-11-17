# routes/auth.py
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from hms.extensions import db
from hms.models.doctor import Doctor
from hms.models.user import User
from hms.services.accounts import AccountsService
from hms.services.audit import AuditService

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == "POST":
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')  # Never strip passwords
        user = User.query.filter_by(email=email, is_active=True).first()

        if user and user.check_password(password):
            login_user(user)
            AuditService.record(
                action='LOGIN_SUCCESS',
                entity_type='User',
                entity_id=user.id,
                actor=user
            )
            flash("Login successful! Welcome back.", "success")
            next_page = request.args.get('next')
            # Prevent open redirects
            if next_page and next_page.startswith('/') and not next_page.startswith('//'):
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            AuditService.record(
                action='LOGIN_FAILED',
                entity_type='User',
                entity_id=getattr(user, 'id', None),
                actor=None,
                after={'attempted_email': email}
            )
            flash("Invalid email or password.", "danger")

    return render_template('auth/login.html')


@auth_bp.route('/signup', methods=['POST', 'GET'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == "POST":
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not all([username, email, password]):
            flash("All fields are required.", "danger")
            return render_template('auth/signup.html')

        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "warning")
            return render_template('auth/signup.html')

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "warning")
            return render_template('auth/signup.html')

        AccountsService.create_user(
            email=email,
            username=username,
            password=password,
            usertype='Patient'
        )
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('auth.login'))

    return render_template('auth/signup.html')


@auth_bp.route('/logout')
@login_required
def logout():
    AuditService.record(
        action='LOGOUT',
        entity_type='User',
        entity_id=current_user.id,
        actor=current_user
    )
    logout_user()
    flash("You have been securely logged out.", "info")
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """B-22: Profile update with current-password re-authentication for sensitive changes."""
    user = db.session.get(User, current_user.id)

    if request.method == 'POST':
        new_username = request.form.get('username', '').strip()
        new_email = request.form.get('email', '').strip().lower()
        new_password = request.form.get('password', '')
        new_phone = request.form.get('phone', '').strip()
        new_gender = request.form.get('gender', '').strip()

        # B-22: Require current password if altering sensitive credentials (email or password)
        if new_password or (new_email and new_email != user.email):
            current_password = request.form.get('current_password', '')
            if not current_password or not user.check_password(current_password):
                flash("Security Verification: You must enter your correct current password to update email or password.", "danger")
                return redirect(url_for('auth.profile'))

        if new_email and new_email != user.email:
            existing_user = User.query.filter(User.email == new_email, User.id != user.id).first()
            if existing_user:
                flash("That email address is already in use by another account.", "danger")
                return redirect(url_for('auth.profile'))
            user.email = new_email

        if new_username and new_username != user.username:
            user.username = new_username

        if new_phone:
            user.phone = new_phone[:20]

        if new_gender:
            user.gender = new_gender

        if new_password:
            if len(new_password) < 8:
                flash("New password must be at least 8 characters long.", "warning")
                return redirect(url_for('auth.profile'))
            user.set_password(new_password)
            AuditService.record(
                action='PASSWORD_CHANGED',
                entity_type='User',
                entity_id=user.id,
                actor=user
            )

        db.session.commit()
        flash("Your profile details have been updated successfully!", "success")
        return redirect(url_for('auth.profile'))

    doctor_info = None
    if current_user.usertype == 'Doctor':
        doctor_info = Doctor.query.filter_by(user_id=current_user.id).first()

    return render_template('auth/profile.html', doctor_info=doctor_info)
