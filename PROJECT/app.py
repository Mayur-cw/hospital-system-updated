from datetime import date
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
import os

# Import our separated config and models
from config import Config
from models import db, Test, User, Patients, MedicalRecord, Doctors, Trigr

# ─────────────────────────────────────────────
# App Configuration
# ─────────────────────────────────────────────

app = Flask(__name__)
app.config.from_object(Config)

# Bind the database to the app
db.init_app(app)

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
# Helper Functions
# ─────────────────────────────────────────────

def is_slot_booked(requested_date, requested_time, target_doctor, current_pid=None):
    """
    Checks if the specific time slot is already booked for the doctor on the given date.
    """
    query = Patients.query.filter_by(date=requested_date, time=requested_time, doctor=target_doctor)
    
    if current_pid:
        query = query.filter(Patients.pid != current_pid)

    return query.first() is not None

# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

# ── Doctors Directory & Registration ──────────────────────────
@app.route('/doctors', methods=['POST', 'GET'])
@login_required
def doctors():
    all_doctors = Doctors.query.all()

    if request.method == "POST":
        email      = request.form.get('email', '').strip()
        doctorname = request.form.get('doctorname', '').strip()
        dept       = request.form.get('dept', '').strip()

        if not all([email, doctorname, dept]):
            flash("All fields are required.", "danger")
            return render_template('doctor.html', all_doctors=all_doctors)

        doctor = Doctors(email=email, doctorname=doctorname, dept=dept)
        db.session.add(doctor)
        db.session.commit()
        flash("Doctor information saved successfully.", "success")
        
        all_doctors = Doctors.query.all()

    return render_template('doctor.html', all_doctors=all_doctors)

# ── API: Get Booked Slots ────────────────────
@app.route('/get_booked_slots', methods=['POST'])
@login_required
def get_booked_slots():
    data = request.get_json()
    req_date = data.get('date')
    req_doctor = data.get('doctor')
    current_pid = data.get('current_pid') 

    if not req_date or not req_doctor:
        return jsonify({'booked_times': []})

    query = Patients.query.filter_by(date=req_date, doctor=req_doctor)
    
    if current_pid:
        query = query.filter(Patients.pid != current_pid)

    bookings = query.all()
    booked_times = [booking.time for booking in bookings]

    return jsonify({'booked_times': booked_times})

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
        doctor  = request.form.get('doctor', '').strip()

        if not all([email, name, gender, slot, disease, time, date, dept, number, doctor]):
            flash("All fields are required.", "danger")
            return render_template('bookings/patient.html', doct=doct)

        if len(number) != 10 or not number.isdigit():
            flash("Please enter a valid 10-digit phone number.", "danger")
            return render_template('bookings/patient.html', doct=doct)

        if is_slot_booked(date, time, doctor):
            flash(f"Slot Unavailable: Dr. {doctor.capitalize()} is already booked at {time}. Please choose another slot.", "warning")
            return redirect(url_for('patient'))

        new_patient = Patients(
            email=email, name=name, gender=gender,
            slot=slot, disease=disease, time=time,
            date=date, dept=dept, number=number, doctor=doctor
        )
        db.session.add(new_patient)
        db.session.commit()
        
        return redirect(url_for('booking_success', pid=new_patient.pid))

    pre_dept = request.args.get('dept', '')
    pre_doc = request.args.get('doctor', '')

    return render_template('bookings/patient.html', doct=doct, pre_dept=pre_dept, pre_doc=pre_doc)

# ── Booking Success Page ─────────────────────
@app.route('/booking_success/<int:pid>')
@login_required
def booking_success(pid):
    appointment = Patients.query.get_or_404(pid)
    
    if current_user.usertype != "Doctor" and appointment.email != current_user.email:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('index'))
        
    return render_template('bookings/booking_success.html', appointment=appointment)

# ── Bookings ─────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.usertype == "Doctor":
        query = Patients.query.filter_by(doctor=current_user.username).order_by(Patients.date.desc()).all()
    else:
        query = Patients.query.filter_by(email=current_user.email).order_by(Patients.date.desc()).all()
    
    return render_template('bookings/booking.html', query=query, page_title="Complete Booking History")

@app.route('/upcoming_bookings')
@login_required
def upcoming_bookings():
    today = date.today()
    if current_user.usertype == "Doctor":
        query = Patients.query.filter(Patients.doctor == current_user.username, Patients.date >= today).order_by(Patients.date.asc()).all()
    else:
        query = Patients.query.filter(Patients.email == current_user.email, Patients.date >= today).order_by(Patients.date.asc()).all()
    
    return render_template('bookings/booking.html', query=query, page_title="Upcoming Appointments")

# ── Medical Records ──────────────────────────
@app.route('/add_record/<int:pid>', methods=['GET', 'POST'])
@login_required
def add_record(pid):
    if current_user.usertype != "Doctor":
        flash("Unauthorized! Only doctors can add medical records.", "danger")
        return redirect(url_for('dashboard'))

    appointment = Patients.query.get_or_404(pid)
    
    existing_record = MedicalRecord.query.filter_by(pid=pid).first()
    if existing_record:
        flash("A medical record already exists for this appointment.", "warning")
        return redirect(url_for('view_record', pid=pid))

    if request.method == "POST":
        diagnosis = request.form.get('diagnosis', '').strip()
        prescription = request.form.get('prescription', '').strip()
        notes = request.form.get('notes', '').strip()
        
        new_record = MedicalRecord(pid=pid, diagnosis=diagnosis, prescription=prescription, notes=notes)
        db.session.add(new_record)
        db.session.commit()
        
        flash("Medical record saved successfully!", "success")
        return redirect(url_for('past_records'))
        
    return render_template('records/add_record.html', appointment=appointment)

@app.route('/view_record/<int:pid>')
@login_required
def view_record(pid):
    appointment = Patients.query.get_or_404(pid)
    record = MedicalRecord.query.filter_by(pid=pid).first()
    
    if current_user.usertype == "Patient" and appointment.email != current_user.email:
        flash("Unauthorized access to medical records.", "danger")
        return redirect(url_for('dashboard'))
    elif current_user.usertype == "Doctor" and appointment.doctor != current_user.username:
         flash("Unauthorized access. You did not attend this patient.", "danger")
         return redirect(url_for('dashboard'))

    if not record:
        flash("No medical record has been generated for this appointment yet.", "info")
        return redirect(url_for('past_records'))
        
    return render_template('records/view_record.html', appointment=appointment, record=record)

@app.route('/past_records')
@login_required
def past_records():
    today = date.today()
    if current_user.usertype == "Doctor":
        query = Patients.query.filter(Patients.doctor == current_user.username, Patients.date < today).order_by(Patients.date.desc()).all()
    else:
        query = Patients.query.filter(Patients.email == current_user.email, Patients.date < today).order_by(Patients.date.desc()).all()
    
    return render_template('bookings/booking.html', query=query, page_title="Past Records & Prescriptions", is_past_record=True)

# ── Edit Booking ─────────────────────────────
@app.route('/edit/<int:pid>', methods=['POST', 'GET'])
@login_required
def edit(pid):
    post = Patients.query.get_or_404(pid)
    doct = Doctors.query.all()

    if current_user.usertype != "Doctor" and post.email != current_user.email:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('upcoming_bookings'))

    if request.method == "POST":
        post.email   = request.form.get('email', '').strip()
        post.name    = request.form.get('name', '').strip()
        post.gender  = request.form.get('gender', '').strip()
        post.slot    = request.form.get('slot', '').strip()
        post.disease = request.form.get('disease', '').strip()
        new_time     = request.form.get('time', '').strip()
        new_date     = request.form.get('date', '').strip()
        post.dept    = request.form.get('dept', '').strip()
        post.number  = request.form.get('number', '').strip()
        new_doctor   = request.form.get('doctor', '').strip()

        if is_slot_booked(new_date, new_time, new_doctor, current_pid=pid):
            flash(f"Update Failed: Dr. {new_doctor.capitalize()} is already booked at {new_time}.", "danger")
            return redirect(url_for('edit', pid=pid))

        post.time = new_time
        post.date = new_date
        post.doctor = new_doctor

        db.session.commit()
        flash("Booking updated successfully.", "success")
        return redirect(url_for('upcoming_bookings'))

    return render_template('bookings/edit.html', posts=post, doct=doct)

# ── Delete Booking ────────────────────────────
@app.route('/delete/<int:pid>', methods=['POST'])
@login_required
def delete(pid):
    patient = Patients.query.get_or_404(pid)

    if current_user.usertype != "Doctor" and patient.email != current_user.email:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('upcoming_bookings'))

    db.session.delete(patient)
    db.session.commit()
    flash("Booking deleted successfully.", "danger")
    return redirect(url_for('upcoming_bookings'))

# ── User Profile ──────────────────────────────
@app.route('/profile', methods=['GET', 'POST'])
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
                return redirect(url_for('profile'))
            user.email = new_email

        if new_username:
            user.username = new_username
            
        user.phone = new_phone
        user.gender = new_gender

        if new_password:
            user.password = generate_password_hash(new_password)

        db.session.commit()
        flash("Your profile details have been updated successfully!", "success")
        return redirect(url_for('profile'))

    return render_template('auth/profile.html')

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
            return render_template('auth/signup.html')

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "warning")
            return render_template('auth/signup.html')

        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username, usertype=usertype, email=email, password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Signup successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('auth/signup.html')

# ── Login ─────────────────────────────────────
@app.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == "POST":
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Login successful!", "success")
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash("Invalid email or password.", "danger")

    return render_template('auth/login.html')

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
    return render_template('admin/trigers.html', posts=posts)

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
    # Keep using app.run for local dev since you renamed main to app
    app.run(debug=os.environ.get('FLASK_DEBUG', 'true').lower() == 'true')