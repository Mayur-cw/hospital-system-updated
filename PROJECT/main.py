from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    UserMixin, LoginManager, login_user,
    logout_user, login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
import os

# ─────────────────────────────────────────────
# App Configuration
# ─────────────────────────────────────────────

app = Flask(__name__)

# Use environment variable for secret key; fallback for dev only
app.secret_key = os.environ.get('SECRET_KEY', 'hmsprojects_dev_key')

# Database URI — set via env var in production
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'mysql://root:Mayur@localhost/hms'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # suppress warning

db = SQLAlchemy(app)

# ─────────────────────────────────────────────
# Login Manager
# ─────────────────────────────────────────────

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Please login to access this page."
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ─────────────────────────────────────────────
# Database Models
# ─────────────────────────────────────────────

class Test(db.Model):
    __tablename__ = 'test'
    id    = db.Column(db.Integer, primary_key=True)
    name  = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    usertype = db.Column(db.String(50), nullable=False)
    email    = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(1000), nullable=False)


class Patients(db.Model):
    __tablename__ = 'patients'
    pid     = db.Column(db.Integer, primary_key=True)
    email   = db.Column(db.String(50), nullable=False)
    name    = db.Column(db.String(50), nullable=False)
    gender  = db.Column(db.String(50), nullable=False)
    slot    = db.Column(db.String(50), nullable=False)
    disease = db.Column(db.String(50), nullable=False)
    time    = db.Column(db.String(50), nullable=False)
    date    = db.Column(db.String(50), nullable=False)
    dept    = db.Column(db.String(50), nullable=False)
    number  = db.Column(db.String(12), nullable=False)


class Doctors(db.Model):
    __tablename__ = 'doctors'
    did        = db.Column(db.Integer, primary_key=True)
    email      = db.Column(db.String(50), nullable=False)
    doctorname = db.Column(db.String(50), nullable=False)
    dept       = db.Column(db.String(100), nullable=False)


class Trigr(db.Model):
    __tablename__ = 'trigr'
    tid       = db.Column(db.Integer, primary_key=True)
    pid       = db.Column(db.Integer, nullable=False)
    email     = db.Column(db.String(50), nullable=False)
    name      = db.Column(db.String(50), nullable=False)
    action    = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.String(50), nullable=False)


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


# ── Doctors ──────────────────────────────────

@app.route('/doctors', methods=['POST', 'GET'])
@login_required
def doctors():
    if request.method == "POST":
        email      = request.form.get('email', '').strip()
        doctorname = request.form.get('doctorname', '').strip()
        dept       = request.form.get('dept', '').strip()

        if not all([email, doctorname, dept]):
            flash("All fields are required.", "danger")
            return render_template('doctor.html')

        doctor = Doctors(email=email, doctorname=doctorname, dept=dept)
        db.session.add(doctor)
        db.session.commit()
        flash("Doctor information saved successfully.", "success")

    return render_template('doctor.html')


# ── Patients ─────────────────────────────────

@app.route('/patients', methods=['POST', 'GET'])
@login_required
def patient():
    doct = Doctors.query.all()

    if request.method == "POST":
        email   = request.form.get('email', '').strip()
        name    = request.form.get('name', '').strip()
        gender  = request.form.get('gender', '').strip()
        slot    = request.form.get('slot', '').strip()
        disease = request.form.get('disease', '').strip()
        time    = request.form.get('time', '').strip()
        date    = request.form.get('date', '').strip()
        dept    = request.form.get('dept', '').strip()
        number  = request.form.get('number', '').strip()

        # Validation
        if not all([email, name, gender, slot, disease, time, date, dept, number]):
            flash("All fields are required.", "danger")
            return render_template('patient.html', doct=doct)

        if len(number) != 10 or not number.isdigit():
            flash("Please enter a valid 10-digit phone number.", "danger")
            return render_template('patient.html', doct=doct)

        new_patient = Patients(
            email=email, name=name, gender=gender,
            slot=slot, disease=disease, time=time,
            date=date, dept=dept, number=number
        )
        db.session.add(new_patient)
        db.session.commit()
        flash("Booking confirmed successfully!", "success")

    return render_template('patient.html', doct=doct)


# ── Bookings ─────────────────────────────────

@app.route('/bookings')
@login_required
def bookings():
    if current_user.usertype == "Doctor":
        query = Patients.query.all()
    else:
        query = Patients.query.filter_by(email=current_user.email).all()

    return render_template('booking.html', query=query)


# ── Edit Booking ─────────────────────────────

@app.route('/edit/<int:pid>', methods=['POST', 'GET'])
@login_required
def edit(pid):
    post = Patients.query.get_or_404(pid)

    # Prevent patients from editing others' bookings
    if current_user.usertype != "Doctor" and post.email != current_user.email:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('bookings'))

    if request.method == "POST":
        post.email   = request.form.get('email', '').strip()
        post.name    = request.form.get('name', '').strip()
        post.gender  = request.form.get('gender', '').strip()
        post.slot    = request.form.get('slot', '').strip()
        post.disease = request.form.get('disease', '').strip()
        post.time    = request.form.get('time', '').strip()
        post.date    = request.form.get('date', '').strip()
        post.dept    = request.form.get('dept', '').strip()
        post.number  = request.form.get('number', '').strip()

        db.session.commit()
        flash("Booking updated successfully.", "success")
        return redirect(url_for('bookings'))

    return render_template('edit.html', posts=post)


# ── Delete Booking ────────────────────────────

@app.route('/delete/<int:pid>', methods=['POST'])  # POST only — never DELETE via GET
@login_required
def delete(pid):
    patient = Patients.query.get_or_404(pid)

    # Prevent patients from deleting others' bookings
    if current_user.usertype != "Doctor" and patient.email != current_user.email:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('bookings'))

    db.session.delete(patient)
    db.session.commit()
    flash("Booking deleted successfully.", "danger")
    return redirect(url_for('bookings'))


# ── Signup ────────────────────────────────────

@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == "POST":
        username = request.form.get('username', '').strip()
        usertype = request.form.get('usertype', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not all([username, usertype, email, password]):
            flash("All fields are required.", "danger")
            return render_template('signup.html')

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "warning")
            return render_template('signup.html')

        # Hash password before storing — NEVER store plain text
        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            usertype=usertype,
            email=email,
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Signup successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('signup.html')


# ── Login ─────────────────────────────────────

@app.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == "POST":
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(email=email).first()

        # check_password_hash compares safely against hashed password
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Login successful!", "success")
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash("Invalid email or password.", "danger")

    return render_template('login.html')


# ── Logout ────────────────────────────────────

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))


# ── Search ────────────────────────────────────

@app.route('/search', methods=['POST', 'GET'])
@login_required
def search():
    if request.method == "POST":
        query_str = request.form.get('search', '').strip()

        if not query_str:
            flash("Please enter a search term.", "warning")
            return render_template('index.html')

        # Search by name OR department
        doctor = Doctors.query.filter(
            (Doctors.doctorname == query_str) |
            (Doctors.dept == query_str)
        ).first()

        if doctor:
            flash(f"Doctor '{doctor.doctorname}' is available in {doctor.dept}.", "success")
        else:
            flash("No doctor found matching that name or department.", "danger")

    return render_template('index.html')


# ── Trigger Logs ──────────────────────────────

@app.route('/details')
@login_required
def details():
    posts = Trigr.query.order_by(Trigr.tid.desc()).all()
    return render_template('trigers.html', posts=posts)


# ── DB Connection Test ────────────────────────

@app.route('/test')
def test():
    try:
        Test.query.all()
        return 'Database connected successfully!'
    except Exception as e:
        return f'Database connection failed: {str(e)}'


# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────

if __name__ == '__main__':
    # debug=True only for development; set to False in production
    app.run(debug=os.environ.get('FLASK_DEBUG', 'true').lower() == 'true')




