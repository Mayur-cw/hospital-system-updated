# routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Doctors

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == "POST":
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Login successful!", "success")
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash("Invalid email or password.", "danger")

    return render_template('auth/login.html')

@auth_bp.route('/signup', methods=['POST', 'GET'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == "POST":
        username = request.form.get('username', '').strip()
        usertype = "Patient"  
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not all([username, email, password]):
            flash("All fields are required.", "danger")
            return render_template('auth/signup.html')

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "warning")
            return render_template('auth/signup.html')

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, usertype=usertype, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash("Signup successful! Please login.", "success")
        return redirect(url_for('auth.login'))

    return render_template('auth/signup.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        new_username = request.form.get('username', '').strip()
        new_email = request.form.get('email', '').strip()
        new_password = request.form.get('password', '').strip()
        new_phone = request.form.get('phone', '').strip()     
        new_gender = request.form.get('gender', '').strip()   

        user = User.query.get(current_user.id)

        if new_email != current_user.email:
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user:
                flash("That email address is already in use by another account.", "danger")
                return redirect(url_for('auth.profile'))
            
            if current_user.usertype == 'Doctor':
                doc_record = Doctors.query.filter_by(email=current_user.email).first()
                if doc_record:
                    doc_record.email = new_email
            user.email = new_email

        if new_username and new_username != current_user.username:
            if current_user.usertype == 'Doctor':
                doc_record = Doctors.query.filter_by(doctorname=current_user.username).first()
                if doc_record:
                    doc_record.doctorname = new_username
            user.username = new_username
            
        user.phone = new_phone
        user.gender = new_gender

        if new_password:
            user.password = generate_password_hash(new_password)

        db.session.commit()
        flash("Your profile details have been updated successfully!", "success")
        return redirect(url_for('auth.profile'))

    doctor_info = None
    if current_user.usertype == 'Doctor':
        doctor_info = Doctors.query.filter_by(email=current_user.email).first()

    return render_template('auth/profile.html', doctor_info=doctor_info)