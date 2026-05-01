from datetime import date
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
import os

from datetime import datetime, date

# Import our separated config and models
from config import Config
from models import db, Test, User, Appointments, MedicalRecord, Doctors, AuditLog # 🚨 UPDATED IMPORT

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

def is_slot_booked(requested_date, requested_time, target_doctor, current_apt_id=None):
    """
    Checks if the specific time slot is already booked for the doctor on the given date.
    """
    query = Appointments.query.filter_by(date=requested_date, time=requested_time, doctor=target_doctor)
    
    if current_apt_id:
        query = query.filter(Appointments.apt_id != current_apt_id)

    return query.first() is not None

# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.route('/')
def index():
    if current_user.is_authenticated and current_user.usertype == 'Doctor':
        today = date.today()
        from datetime import datetime
        now = datetime.now().time()

        todays_appointments = Appointments.query.filter_by(
            doctor=current_user.username, 
            date=today
        ).all()

        todays_appointments.sort(key=lambda x: datetime.strptime(x.time, '%I:%M %p').time())

        total_today = len(todays_appointments)

        unverified_active = []
        next_patient = None
        
        # New Strict Counters for the Filter Cards
        completed_count = 0
        waiting_count = 0
        pending_rx_count = 0 
        
        prescribed_apt_ids = [r.apt_id for r in MedicalRecord.query.all()]

        for apt in todays_appointments:
            apt_time = datetime.strptime(apt.time, '%I:%M %p').time()
            apt.is_active = (apt_time <= now)

            # 🚨 NEW: Categorize every patient for the JS Filters
            if apt.apt_id in prescribed_apt_ids or apt.slot == 'Completed':
                apt.category = 'completed'
                completed_count += 1
            elif apt.slot == 'Missed':
                apt.category = 'missed'
            elif apt.slot == 'Attended':
                apt.category = 'pending_rx'
                pending_rx_count += 1
            else:
                apt.category = 'waiting'
                waiting_count += 1
                if apt.is_active:
                    unverified_active.append(apt)
                else:
                    if not next_patient:
                        next_patient = apt

        if unverified_active:
            unverified_active.sort(key=lambda x: datetime.strptime(x.time, '%I:%M %p').time(), reverse=True)
            current_patient = unverified_active[0]
        else:
            current_patient = None

        formatted_date = today.strftime('%A, %b %d, %Y')

        return render_template('index.html', 
                               all_queue=todays_appointments, # Pass EVERYONE
                               total_today=total_today,
                               current_patient=current_patient,
                               next_patient=next_patient,
                               waiting_count=waiting_count,
                               completed_count=completed_count,
                               pending_rx_count=pending_rx_count, # Pass new strict counter
                               today_date=formatted_date)

    return render_template('index.html')

@app.route('/doctors', methods=['GET'])
@login_required
def doctors():
    all_doctors = Doctors.query.all()
    return render_template('doctor.html', all_doctors=all_doctors)

@app.route('/get_booked_slots', methods=['POST'])
@login_required
def get_booked_slots():
    data = request.get_json()
    req_date = data.get('date')
    req_doctor = data.get('doctor')
    current_apt_id = data.get('current_pid') 

    if not req_date or not req_doctor:
        return jsonify({'booked_times': []})

    query = Appointments.query.filter_by(date=req_date, doctor=req_doctor)
    
    if current_apt_id:
        query = query.filter(Appointments.apt_id != current_apt_id)

    bookings = query.all()
    booked_times = [booking.time for booking in bookings]

    return jsonify({'booked_times': booked_times})

@app.route('/patients', methods=['POST', 'GET'])
@login_required
def patient():
    doct = Doctors.query.all()

    if request.method == "POST":
        # 🚨 NORMALIZATION FIX: We no longer pull personal info from the form!
        slot    = request.form.get('slot', '').strip()
        disease = request.form.get('disease', '').strip()
        time    = request.form.get('time', '').strip()
        date    = request.form.get('date', '').strip()
        dept    = request.form.get('dept', '').strip()
        doctor  = request.form.get('doctor', '').strip()

        if not all([slot, disease, time, date, dept, doctor]):
            flash("All fields are required.", "danger")
            return render_template('bookings/patient.html', doct=doct)

        try:
            appointment_date = datetime.strptime(date, '%Y-%m-%d').date()
            today_date = datetime.today().date()
            
            if appointment_date < today_date:
                flash("Error: You cannot book an appointment in the past.", "danger")
                return redirect(url_for('patient'))
                
            if appointment_date == today_date:
                appointment_time = datetime.strptime(time, '%I:%M %p').time()
                current_time = datetime.now().time()
                
                if appointment_time < current_time:
                    flash("Error: That time slot has already passed today. Please select a future time.", "danger")
                    return redirect(url_for('patient'))
                    
        except ValueError:
            flash("Invalid date or time format.", "danger")
            return redirect(url_for('patient'))

        if is_slot_booked(date, time, doctor):
            flash(f"Slot Unavailable: Dr. {doctor.capitalize()} is already booked at {time}. Please choose another slot.", "warning")
            return redirect(url_for('patient'))

        # 🚨 NORMALIZATION FIX: Create appointment using the Foreign Key user_id
        new_appointment = Appointments(
            user_id=current_user.id, 
            slot=slot, disease=disease, time=time,
            date=date, dept=dept, doctor=doctor
        )
        db.session.add(new_appointment)
        db.session.commit()
        
        return redirect(url_for('booking_success', apt_id=new_appointment.apt_id))

    pre_dept = request.args.get('dept', '')
    pre_doc = request.args.get('doctor', '')

    return render_template('bookings/patient.html', doct=doct, pre_dept=pre_dept, pre_doc=pre_doc)

@app.route('/booking_success/<int:apt_id>')
@login_required
def booking_success(apt_id):
    appointment = Appointments.query.get_or_404(apt_id)
    
    # 🚨 NORMALIZATION FIX: Compare user_id instead of email
    if current_user.usertype != "Doctor" and appointment.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('index'))
        
    return render_template('bookings/booking_success.html', appointment=appointment)

@app.route('/mark_missed/<int:apt_id>', methods=['POST'])
@login_required
def mark_missed(apt_id):
    if current_user.usertype != "Doctor":
        flash("Unauthorized!", "danger")
        return redirect(url_for('dashboard'))

    appointment = Appointments.query.get_or_404(apt_id)
    appointment.slot = 'Missed'
    db.session.commit()
    
    flash(f"Appointment for {appointment.patient.username} marked as Missed.", "info")
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/mark_attended/<int:apt_id>', methods=['POST'])
@login_required
def mark_attended(apt_id):
    if current_user.usertype != "Doctor":
        flash("Unauthorized!", "danger")
        return redirect(url_for('dashboard'))

    appointment = Appointments.query.get_or_404(apt_id)
    appointment.slot = 'Attended'
    db.session.commit()
    
    flash(f"{appointment.patient.username} marked as Attended. Prescription is now pending.", "success")
    return redirect(request.referrer or url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    from datetime import datetime

    if current_user.usertype == "Doctor":
        query = Appointments.query.filter_by(doctor=current_user.username).all()
    else:
        query = Appointments.query.filter_by(user_id=current_user.id).all()
    
    query.sort(key=lambda x: datetime.strptime(f"{x.date} {x.time}", '%Y-%m-%d %I:%M %p'), reverse=True)
    records = MedicalRecord.query.all()
    prescribed_apt_ids = [r.apt_id for r in records]
    
    # 🚨 RENAMED: This is now the master 'Appointment Log'
    return render_template('bookings/booking.html', query=query, page_title="Appointment Log", prescribed_apt_ids=prescribed_apt_ids)

@app.route('/upcoming_bookings')
@login_required
def upcoming_bookings():
    today = date.today()
    from datetime import datetime
    now = datetime.now().time()

    if current_user.usertype == "Doctor":
        raw_query = Appointments.query.filter(
            Appointments.doctor == current_user.username, 
            Appointments.date >= today
        ).all()
    else:
        # 🚨 NORMALIZATION FIX
        raw_query = Appointments.query.filter(
            Appointments.user_id == current_user.id, 
            Appointments.date >= today
        ).all()
    
    records = MedicalRecord.query.all()
    prescribed_apt_ids = [r.apt_id for r in records]

    upcoming_list = []
    for apt in raw_query:
        apt_time = datetime.strptime(apt.time, '%I:%M %p').time()
        if apt.date == today and apt_time <= now:
            continue
        if apt.slot in ['Completed', 'Missed', 'Attended'] or apt.apt_id in prescribed_apt_ids:
            continue
        upcoming_list.append(apt)
        
    upcoming_list.sort(key=lambda x: datetime.strptime(f"{x.date} {x.time}", '%Y-%m-%d %I:%M %p'))

    return render_template('bookings/booking.html', query=upcoming_list, page_title="Upcoming Appointments", prescribed_apt_ids=[])

@app.route('/add_record/<int:apt_id>', methods=['GET', 'POST'])
@login_required
def add_record(apt_id):
    if current_user.usertype != "Doctor":
        flash("Unauthorized! Only doctors can add medical records.", "danger")
        return redirect(url_for('dashboard'))

    appointment = Appointments.query.get_or_404(apt_id)
    
    existing_record = MedicalRecord.query.filter_by(apt_id=apt_id).first()
    if existing_record:
        flash("A medical record already exists for this appointment.", "warning")
        return redirect(url_for('view_record', apt_id=apt_id))

    if request.method == "POST":
        diagnosis = request.form.get('diagnosis', '').strip()
        prescription = request.form.get('prescription', '').strip()
        notes = request.form.get('notes', '').strip()
        
        new_record = MedicalRecord(apt_id=apt_id, diagnosis=diagnosis, prescription=prescription, notes=notes)
        db.session.add(new_record)
        
        appointment.slot = 'Completed'
        db.session.commit()
        
        flash("Medical record saved successfully!", "success")
        return redirect(url_for('index'))
        
    return render_template('records/add_record.html', appointment=appointment)

@app.route('/view_record/<int:apt_id>')
@login_required
def view_record(apt_id):
    appointment = Appointments.query.get_or_404(apt_id)
    record = MedicalRecord.query.filter_by(apt_id=apt_id).first()
    
    # 🚨 NORMALIZATION FIX
    if current_user.usertype == "Patient" and appointment.user_id != current_user.id:
        flash("Unauthorized access to medical records.", "danger")
        return redirect(url_for('dashboard'))
    elif current_user.usertype == "Doctor" and appointment.doctor.lower() != current_user.username.lower():
         flash("Unauthorized access. You did not attend this patient.", "danger")
         return redirect(url_for('dashboard'))

    if not record:
        flash("No medical record has been generated for this appointment yet.", "info")
        return redirect(url_for('past_records'))
        
    return render_template('records/view_record.html', appointment=appointment, record=record)

@app.route('/edit_record/<int:apt_id>', methods=['GET', 'POST'])
@login_required
def edit_record(apt_id):
    if current_user.usertype != "Doctor":
        flash("Unauthorized! Only doctors can edit medical records.", "danger")
        return redirect(url_for('dashboard'))

    appointment = Appointments.query.get_or_404(apt_id)
    record = MedicalRecord.query.filter_by(apt_id=apt_id).first()

    if not record:
        flash("No medical record exists to edit yet.", "warning")
        return redirect(url_for('add_record', apt_id=apt_id))

    if appointment.doctor.lower() != current_user.username.lower():
         flash("Unauthorized access. You cannot edit another doctor's patient record.", "danger")
         return redirect(url_for('dashboard'))

    if request.method == "POST":
        record.diagnosis = request.form.get('diagnosis', '').strip()
        record.prescription = request.form.get('prescription', '').strip()
        record.notes = request.form.get('notes', '').strip()
        
        db.session.commit()
        flash(f"Medical record for {appointment.patient.username} updated successfully!", "success")
        return redirect(url_for('past_records'))
        
    return render_template('records/edit_record.html', appointment=appointment, record=record)

@app.route('/past_records')
@login_required
def past_records():
    from datetime import datetime, date
    
    today_str = str(date.today()) 

    records = MedicalRecord.query.all()
    prescribed_apt_ids = [r.apt_id for r in records]

    if current_user.usertype == "Doctor":
        raw_query = Appointments.query.filter_by(doctor=current_user.username).all()
    else:
        raw_query = Appointments.query.filter_by(user_id=current_user.id).all()
    
    history_list = []
    
    # 🚨 THE STRICT CLINICAL FILTER
    for apt in raw_query:
        is_completed = (apt.apt_id in prescribed_apt_ids) or (apt.slot == 'Completed')
        is_pending_rx = (apt.slot == 'Attended')
        # Catch unverified past appointments, but explicitly EXCLUDE 'Missed'
        is_past_unverified = (str(apt.date) < today_str and apt.slot not in ['Completed', 'Attended', 'Missed'])
        
        if is_completed or is_pending_rx or is_past_unverified:
            history_list.append(apt)

    history_list.sort(key=lambda x: datetime.strptime(f"{x.date} {x.time}", '%Y-%m-%d %I:%M %p'), reverse=True)
    
    # 🚨 RENAMED BACK: Remains 'Patient History'
    return render_template('bookings/booking.html', query=history_list, page_title="Patient History", is_past_record=True, prescribed_apt_ids=prescribed_apt_ids)

@app.route('/edit/<int:apt_id>', methods=['POST', 'GET'])
@login_required
def edit(apt_id):
    post = Appointments.query.get_or_404(apt_id)
    doct = Doctors.query.all()

    # 🚨 NORMALIZATION FIX
    if current_user.usertype != "Doctor" and post.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('upcoming_bookings'))

    if request.method == "POST":
        # 🚨 NORMALIZATION FIX: Only updating the booking details, NOT personal info!
        post.slot    = request.form.get('slot', '').strip()
        post.disease = request.form.get('disease', '').strip()
        new_time     = request.form.get('time', '').strip()
        new_date     = request.form.get('date', '').strip()
        post.dept    = request.form.get('dept', '').strip()
        new_doctor   = request.form.get('doctor', '').strip()

        if is_slot_booked(new_date, new_time, new_doctor, current_apt_id=apt_id):
            flash(f"Update Failed: Dr. {new_doctor.capitalize()} is already booked at {new_time}.", "danger")
            return redirect(url_for('edit', apt_id=apt_id))

        post.time = new_time
        post.date = new_date
        post.doctor = new_doctor

        db.session.commit()
        flash("Booking updated successfully.", "success")
        return redirect(url_for('upcoming_bookings'))

    return render_template('bookings/edit.html', posts=post, doct=doct)

@app.route('/delete/<int:apt_id>', methods=['POST'])
@login_required
def delete(apt_id):
    appointment = Appointments.query.get_or_404(apt_id)

    # 🚨 NORMALIZATION FIX
    if current_user.usertype != "Doctor" and appointment.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('upcoming_bookings'))

    db.session.delete(appointment)
    db.session.commit()
    flash("Booking deleted successfully.", "danger")
    return redirect(url_for('upcoming_bookings'))

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
        return redirect(url_for('profile'))

    doctor_info = None
    if current_user.usertype == 'Doctor':
        doctor_info = Doctors.query.filter_by(email=current_user.email).first()

    return render_template('auth/profile.html', doctor_info=doctor_info)

@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

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
        new_user = User(
            username=username, usertype=usertype, email=email, password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Signup successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('auth/signup.html')

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

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/search', methods=['POST', 'GET'])
@login_required
def search():
    if request.method == "POST":
        query_str = request.form.get('search', '').strip()

        if not query_str:
            flash("Please enter a search term.", "warning")
            return redirect(request.referrer or url_for('index'))

        search_term = f"%{query_str}%"

        # 🚨 SMART SEARCH FIX: Use SQLAlchemy .join() to search the User table via the Appointment
        if current_user.usertype == 'Doctor':
            results = Appointments.query.join(User).filter(
                Appointments.doctor == current_user.username,
                (User.username.ilike(search_term)) | 
                (User.email.ilike(search_term)) | 
                (User.phone.ilike(search_term))
            ).order_by(Appointments.date.desc()).all()
            
            if not results:
                flash(f"No patients found matching '{query_str}'.", "warning")
                return redirect(request.referrer or url_for('index'))
                
            return render_template('bookings/booking.html', query=results, page_title=f"Patient Search Results: '{query_str}'", prescribed_apt_ids=[r.apt_id for r in MedicalRecord.query.all()])

        else:
            doctors = Doctors.query.filter(
                (Doctors.doctorname.ilike(search_term)) |
                (Doctors.dept.ilike(search_term))
            ).all()

            if doctors:
                flash(f"Found {len(doctors)} matching doctor(s) or department(s). Check the Directory below!", "success")
                return redirect(url_for('doctors'))
            else:
                flash(f"No doctor or department found matching '{query_str}'.", "danger")
                return redirect(request.referrer or url_for('index'))

    return redirect(url_for('index'))

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.usertype != "Admin":
        flash("Unauthorized Access! Administrator privileges required.", "danger")
        return redirect(url_for('index'))

    total_doctors = Doctors.query.count()
    total_users = User.query.filter_by(usertype='Patient').count()
    total_appointments = Appointments.query.count()
    
    # 🚨 UPDATED: AuditLog instead of Trigr
    recent_logs = AuditLog.query.order_by(AuditLog.tid.desc()).limit(5).all()

    return render_template('admin/admin.html', 
                           total_doctors=total_doctors, 
                           total_users=total_users, 
                           total_appointments=total_appointments,
                           recent_logs=recent_logs)

@app.route('/add_staff', methods=['POST'])
@login_required
def add_staff():
    if current_user.usertype != "Admin":
        flash("Unauthorized! Only Admins can create staff accounts.", "danger")
        return redirect(url_for('index'))

    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    usertype = request.form.get('usertype', '').strip()
    dept = request.form.get('dept', '').strip()

    if User.query.filter_by(email=email).first():
        flash("An account with that email already exists.", "warning")
        return redirect(url_for('admin_dashboard'))

    hashed_password = generate_password_hash(password)
    new_user = User(username=username, usertype=usertype, email=email, password=hashed_password)
    db.session.add(new_user)
    
    if usertype == "Doctor":
        new_doc = Doctors(email=email, doctorname=username, dept=dept)
        db.session.add(new_doc)
        
    db.session.commit()
    flash(f"Success! {usertype} account for {username} has been provisioned.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/details')
@login_required
def details():
    # 🚨 UPDATED: AuditLog instead of Trigr
    posts = AuditLog.query.order_by(AuditLog.tid.desc()).all()
    return render_template('admin/trigers.html', posts=posts)

@app.route('/test')
def test():
    try:
        Test.query.all()
        return 'Database connected successfully!'
    except Exception as e:
        return f'Database connection failed: {str(e)}'

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', 'true').lower() == 'true')