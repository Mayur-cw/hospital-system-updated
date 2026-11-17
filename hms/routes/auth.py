# routes/auth.py
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from hms.extensions import db, limiter
from hms.models.doctor import Doctor
from hms.models.user import User
from hms.services.accounts import AccountsService
from hms.services.audit import AuditService
from hms.utils.security import (
    generate_token,
    safe_redirect,
    validate_password_strength,
    verify_token,
)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST', 'GET'])
@limiter.limit("15 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == "POST":
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')  # S-06: Never strip passwords
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
            # S-03: Safe redirect validation
            return safe_redirect(request.args.get('next'), fallback='main.index')
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
@limiter.limit("10 per minute")
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

        # S-06: Password strength verification (min 10 chars, not on breach list)
        is_valid_pw, pw_err = validate_password_strength(password)
        if not is_valid_pw:
            flash(pw_err, "warning")
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


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """S-02: Logout via POST with CSRF guard."""
    AuditService.record(
        action='LOGOUT',
        entity_type='User',
        entity_id=current_user.id,
        actor=current_user
    )
    logout_user()
    flash("You have been securely logged out.", "info")
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def forgot_password():
    """S-12: Password reset request generating signed expiring token."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email, is_active=True).first()

        if user:
            token = generate_token({'user_id': user.id}, current_app.config['SECRET_KEY'])
            AuditService.record(
                action='PASSWORD_RESET_REQUESTED',
                entity_type='User',
                entity_id=user.id,
                actor=user
            )
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            # In production, dispatch email; in development/testing, show token url in flash/logs
            flash(f"If an account exists for {email}, a password reset link has been issued. (Demo/Dev Link: {reset_url})", "info")
        else:
            flash(f"If an account exists for {email}, a password reset link has been issued.", "info")

        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """S-12: Password reset with expiring token verification."""
    data = verify_token(token, current_app.config['SECRET_KEY'], max_age_seconds=1800)
    if not data or 'user_id' not in data:
        flash("This password reset link is invalid or has expired. Please request a new one.", "danger")
        return redirect(url_for('auth.forgot_password'))

    user = db.session.get(User, data['user_id'])
    if not user or not user.is_active:
        flash("User account not found or deactivated.", "danger")
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if new_password != confirm_password:
            flash("Passwords do not match.", "warning")
            return render_template('auth/reset_password.html', token=token)

        is_valid_pw, pw_err = validate_password_strength(new_password)
        if not is_valid_pw:
            flash(pw_err, "warning")
            return render_template('auth/reset_password.html', token=token)

        user.set_password(new_password)
        db.session.commit()

        AuditService.record(
            action='PASSWORD_RESET_COMPLETED',
            entity_type='User',
            entity_id=user.id,
            actor=user
        )
        flash("Your password has been successfully reset. Please log in with your new password.", "success")
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)


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
            is_valid_pw, pw_err = validate_password_strength(new_password)
            if not is_valid_pw:
                flash(pw_err, "warning")
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
