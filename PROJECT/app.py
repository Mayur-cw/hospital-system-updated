import os
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

# Import our separated config and models
from config import Config
from models import db, Test, User, Appointments, MedicalRecord, Doctors, AuditLog 

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

    bookings = query.all()
    
    # If an appointment is Cancelled or Missed, the slot becomes available again!
    active_bookings = [b for b in bookings if b.slot not in ['Cancelled', 'Missed']]

    return len(active_bookings) > 0

# ─────────────────────────────────────────────
# Core Routes
# ─────────────────────────────────────────────

@app.route('/')
def index():

    if current_user.usertype == 'Admin':
            return redirect(url_for('admin_dashboard'))
    
    if current_user.is_authenticated and current_user.usertype == 'Doctor':
        today = date.today()
        now = datetime.now().time()

        todays_appointments = Appointments.query.filter_by(
            doctor=current_user.username, 
            date=today
        ).all()

        todays_appointments.sort(key=lambda x: datetime.strptime(x.time, '%I:%M %p').time())

        total_today = len(todays_appointments)

        unverified_active = []
        next_patient = None
        
        completed_count = 0
        waiting_count = 0
        pending_rx_count = 0 
        
        prescribed_apt_ids = [r.apt_id for r in MedicalRecord.query.all()]

        for apt in todays_appointments:
            apt_time = datetime.strptime(apt.time, '%I:%M %p').time()
            apt.is_active = (apt_time <= now)

            if apt.apt_id in prescribed_apt_ids or apt.slot == 'Completed':
                apt.category = 'completed'
                completed_count += 1
            elif apt.slot == 'Missed':
                apt.category = 'missed'
            elif apt.slot == 'Cancelled':
                apt.category = 'cancelled'
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
                               all_queue=todays_appointments, 
                               total_today=total_today,
                               current_patient=current_patient,
                               next_patient=next_patient,
                               waiting_count=waiting_count,
                               completed_count=completed_count,
                               pending_rx_count=pending_rx_count, 
                               today_date=formatted_date)

# ==========================================
# 🧑‍🤝‍🧑 PATIENT DASHBOARD LOGIC
# ==========================================
    elif current_user.usertype == 'Patient':
        today = date.today()
        now = datetime.now().time()
            
        # Fetch all upcoming appointments
        raw_upcoming = Appointments.query.filter(
            Appointments.user_id == current_user.id,
            Appointments.date >= today
        ).all()
        
        upcoming_list = []
        for apt in raw_upcoming:
            apt_time = datetime.strptime(apt.time, '%I:%M %p').time()
            # Skip past times today
            if apt.date == str(today) and apt_time <= now:
                continue
            # Only show 'Scheduled' in the upcoming widget
            if apt.slot == 'Scheduled': 
                upcoming_list.append(apt)
                
        # Sort by date and time
        upcoming_list.sort(key=lambda x: datetime.strptime(f"{x.date} {x.time}", '%Y-%m-%d %I:%M %p'))
        
        # Slice the top 5
        upcoming_appointments = upcoming_list[:5]
        
        return render_template('index.html', 
                                upcoming_appointments=upcoming_appointments, 
                                today_date=today.strftime('%A, %b %d, %Y'))


    return render_template('index.html')

@app.route('/doctors', methods=['GET'])
@login_required
def doctors():
    all_doctors = Doctors.query.all()
    return render_template('doctor_directory.html', all_doctors=all_doctors)

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
    booked_times = [b.time for b in bookings if b.slot not in ['Cancelled', 'Missed']]

    return jsonify({'booked_times': booked_times})

@app.route('/patients', methods=['POST', 'GET'])
@login_required
def patient():
    doct = Doctors.query.all()

    if request.method == "POST":
        slot    = request.form.get('slot', '').strip()
        disease = request.form.get('disease', '').strip()
        time    = request.form.get('time', '').strip()
        date_str= request.form.get('date', '').strip()
        dept    = request.form.get('dept', '').strip()
        doctor  = request.form.get('doctor', '').strip()

        if not all([slot, disease, time, date_str, dept, doctor]):
            flash("All fields are required.", "danger")
            return render_template('bookings/book_appointment.html', doct=doct)

        try:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
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

        if is_slot_booked(date_str, time, doctor):
            flash(f"Slot Unavailable: Dr. {doctor.capitalize()} is already booked at {time}. Please choose another slot.", "warning")
            return redirect(url_for('patient'))

        new_appointment = Appointments(
            user_id=current_user.id, 
            slot=slot, disease=disease, time=time,
            date=date_str, dept=dept, doctor=doctor
        )
        db.session.add(new_appointment)
        db.session.commit()
        
        return redirect(url_for('booking_success', apt_id=new_appointment.apt_id))

    pre_dept = request.args.get('dept', '')
    pre_doc = request.args.get('doctor', '')

    return render_template('bookings/book_appointment.html', doct=doct, pre_dept=pre_dept, pre_doc=pre_doc)

@app.route('/booking_success/<int:apt_id>')
@login_required
def booking_success(apt_id):
    appointment = Appointments.query.get_or_404(apt_id)
    if current_user.usertype != "Doctor" and appointment.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('index'))
    return render_template('bookings/booking_success.html', appointment=appointment)

@app.route('/cancel_apt/<int:apt_id>', methods=['POST'])
@login_required
def cancel_apt(apt_id):
    appointment = Appointments.query.get_or_404(apt_id)
    if current_user.usertype == "Patient" and appointment.user_id != current_user.id:
        flash("Unauthorized! You can only cancel your own appointments.", "danger")
        return redirect(request.referrer or url_for('upcoming_bookings'))
    elif current_user.usertype == "Doctor" and appointment.doctor.lower() != current_user.username.lower():
         flash("Unauthorized! You can only cancel your own schedule.", "danger")
         return redirect(request.referrer or url_for('dashboard'))

    appointment.slot = 'Cancelled'
    db.session.commit()
    flash("Appointment has been successfully cancelled.", "warning")
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/mark_missed/<int:apt_id>', methods=['POST'])
@login_required
def mark_missed(apt_id):
    if current_user.usertype != "Doctor":
        flash("Unauthorized!", "danger")
        return redirect(url_for('dashboard'))
    appointment = Appointments.query.get_or_404(apt_id)
    appointment.slot = 'Missed'
    db.session.commit()
    flash(f"Appointment marked as Missed.", "info")
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
    flash(f"Patient marked as Attended. Prescription is now pending.", "success")
    return redirect(request.referrer or url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.usertype == "Doctor":
        query = Appointments.query.filter_by(doctor=current_user.username).all()
    else:
        query = Appointments.query.filter_by(user_id=current_user.id).all()
    
    query.sort(key=lambda x: datetime.strptime(f"{x.date} {x.time}", '%Y-%m-%d %I:%M %p'), reverse=True)
    records = MedicalRecord.query.all()
    prescribed_apt_ids = [r.apt_id for r in records]
    
    return render_template('bookings/appointment_history.html', query=query, page_title="Appointment Log", prescribed_apt_ids=prescribed_apt_ids)

@app.route('/upcoming_bookings')
@login_required
def upcoming_bookings():
    today = date.today()
    now = datetime.now().time()

    if current_user.usertype == "Doctor":
        raw_query = Appointments.query.filter(
            Appointments.doctor == current_user.username, 
            Appointments.date >= today
        ).all()
    else:
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
        if apt.slot in ['Completed', 'Missed', 'Attended', 'Cancelled'] or apt.apt_id in prescribed_apt_ids:
            continue
        upcoming_list.append(apt)
        
    upcoming_list.sort(key=lambda x: datetime.strptime(f"{x.date} {x.time}", '%Y-%m-%d %I:%M %p'))

    return render_template('bookings/appointment_history.html', query=upcoming_list, page_title="Upcoming Appointments", prescribed_apt_ids=[])

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
    
    if current_user.usertype == "Patient" and appointment.user_id != current_user.id:
        flash("Unauthorized access to medical records.", "danger")
        return redirect(url_for('dashboard'))
    elif current_user.usertype == "Doctor" and appointment.doctor.lower() != current_user.username.lower():
         flash("Unauthorized access. You did not attend this patient.", "danger")
         return redirect(url_for('dashboard'))

    if not record:
        flash("No medical record has been generated yet.", "info")
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
        flash("Medical record updated successfully!", "success")
        return redirect(url_for('past_records'))
        
    return render_template('records/edit_record.html', appointment=appointment, record=record)

@app.route('/past_records')
@login_required
def past_records():
    today_str = str(date.today()) 
    records = MedicalRecord.query.all()
    prescribed_apt_ids = [r.apt_id for r in records]

    if current_user.usertype == "Doctor":
        raw_query = Appointments.query.filter_by(doctor=current_user.username).all()
    else:
        raw_query = Appointments.query.filter_by(user_id=current_user.id).all()
    
    history_list = []
    for apt in raw_query:
        is_completed = (apt.apt_id in prescribed_apt_ids) or (apt.slot == 'Completed')
        is_pending_rx = (apt.slot == 'Attended')
        is_past_unverified = (str(apt.date) < today_str and apt.slot not in ['Completed', 'Attended', 'Missed', 'Cancelled'])
        
        if is_completed or is_pending_rx or is_past_unverified:
            history_list.append(apt)

    history_list.sort(key=lambda x: datetime.strptime(f"{x.date} {x.time}", '%Y-%m-%d %I:%M %p'), reverse=True)
    return render_template('bookings/appointment_history.html', query=history_list, page_title="Patient History", is_past_record=True, prescribed_apt_ids=prescribed_apt_ids)

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
        new_user = User(username=username, usertype=usertype, email=email, password=hashed_password)
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


# ─────────────────────────────────────────────
# 👑 NEW MODULAR ADMIN ROUTES (SQLAlchemy)
# ─────────────────────────────────────────────

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.usertype != "Admin":
        flash("Unauthorized Access! Administrator privileges required.", "danger")
        return redirect(url_for('index'))

    total_doctors = Doctors.query.count()
    total_users = User.query.filter_by(usertype='Patient').count()
    total_appointments = Appointments.query.count()
    recent_logs = AuditLog.query.order_by(AuditLog.tid.desc()).limit(5).all()

    return render_template('admin/admin_dashboard.html', 
                           total_doctors=total_doctors, 
                           total_users=total_users, 
                           total_appointments=total_appointments,
                           recent_logs=recent_logs)

@app.route('/details')
@login_required
def details():
    if current_user.usertype != "Admin":
        flash("Unauthorized Access!", "danger")
        return redirect(url_for('index'))

    # Join AuditLog with User to get names and emails for the template safely
    logs_data = db.session.query(AuditLog, User).outerjoin(User, AuditLog.user_id == User.id).order_by(AuditLog.tid.desc()).all()
    
    posts = []
    for log, user in logs_data:
        posts.append({
            'tid': log.tid,
            'pid': log.user_id,  # <--- Change this from log.pid to log.user_id
            'action': log.action,
            'timestamp': log.timestamp,
            'email': user.email if user else 'Deleted/Unknown',
            'name': user.username if user else 'Deleted/Unknown'
        })

    return render_template('admin/audit_logs.html', posts=posts)


@app.route('/admin/doctors')
@login_required
def admin_doctors():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))

    # Build a clean list connecting User accounts and Doctor info
    doc_users = User.query.filter_by(usertype='Doctor').all()
    doctors_list = []
    for u in doc_users:
        doc_record = Doctors.query.filter_by(email=u.email).first()
        doctors_list.append({
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'dept': doc_record.dept if doc_record else ''
        })

    return render_template('admin/admin_doctors.html', doctors=doctors_list)


@app.route('/admin/edit_doctor', methods=['POST'])
@login_required
def admin_edit_doctor():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))

    doctor_id = request.form.get('doctor_id')
    username  = request.form.get('username')
    email     = request.form.get('email')
    dept      = request.form.get('dept')

    u = User.query.get(doctor_id)
    if u and u.usertype == 'Doctor':
        old_email = u.email
        u.username = username
        u.email = email
        
        doc = Doctors.query.filter_by(email=old_email).first()
        if doc:
            doc.doctorname = username
            doc.email = email
            doc.dept = dept
            
        db.session.commit()
        flash(f'Doctor {username} updated successfully.', 'success')

    return redirect(url_for('admin_doctors'))


@app.route('/admin/change_doctor_password', methods=['POST'])
@login_required
def admin_change_doctor_password():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))

    doctor_id        = request.form.get('doctor_id')
    new_password     = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if new_password != confirm_password:
        flash('Passwords do not match. Please try again.', 'danger')
        return redirect(url_for('admin_doctors'))

    u = User.query.get(doctor_id)
    if u and u.usertype == 'Doctor':
        u.password = generate_password_hash(new_password)
        db.session.commit()
        flash('Doctor password updated successfully.', 'success')

    return redirect(url_for('admin_doctors'))


@app.route('/admin/delete_doctor', methods=['POST'])
@login_required
def admin_delete_doctor():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))

    doctor_id = request.form.get('doctor_id')
    u = User.query.get(doctor_id)
    if u and u.usertype == 'Doctor':
        doc = Doctors.query.filter_by(email=u.email).first()
        if doc:
            db.session.delete(doc)
        db.session.delete(u)
        db.session.commit()
        flash('Doctor account removed successfully.', 'success')

    return redirect(url_for('admin_doctors'))


@app.route('/admin/patients')
@login_required
def admin_patients():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))

    search_query = request.args.get('search', '').strip()
    
    query = User.query.filter_by(usertype='Patient')
    if search_query:
        search_term = f'%{search_query}%'
        query = query.filter((User.username.ilike(search_term)) | (User.email.ilike(search_term)))
    
    patients_list = []
    for p in query.all():
        appt_count = Appointments.query.filter_by(user_id=p.id).count()
        patients_list.append({
            'id': p.id,
            'username': p.username,
            'email': p.email,
            'phone': p.phone,
            'gender': p.gender,
            'appointment_count': appt_count
        })

    return render_template('admin/admin_patients.html', patients=patients_list, search_query=search_query)


@app.route('/admin/appointments')
@login_required
def admin_appointments():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))

    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    
    selected_date = request.args.get('date', today)
    selected_doctor = request.args.get('doctor_id', '')
    search_query = request.args.get('search', '').strip()

    q = Appointments.query

    if selected_date:
        q = q.filter(Appointments.date == selected_date)
        
    doctor_name = ''
    if selected_doctor:
        doc_user = User.query.get(selected_doctor)
        if doc_user:
            q = q.filter(Appointments.doctor == doc_user.username)
            doctor_name = doc_user.username
            
    if search_query:
        search_term = f'%{search_query}%'
        q = q.join(User, Appointments.user_id == User.id).filter(
            (User.username.ilike(search_term)) | (User.email.ilike(search_term))
        )

    # Sort effectively
    appts = q.order_by(Appointments.date.desc(), Appointments.time.asc()).all()

    appt_data = []
    for a in appts:
        u = User.query.get(a.user_id)
        # Try to map status cleanly
        status = a.slot
        if status in ['Scheduled']: status = 'Pending'
        
        appt_data.append({
            'id': a.apt_id,
            'patient_name': u.username if u else 'Unknown',
            'patient_email': u.email if u else 'Unknown',
            'doctor_name': a.doctor,
            'dept': a.dept,
            'appointment_date': a.date,
            'time_slot': a.time,
            'status': status
        })

    # Get doctors for dropdown
    doc_users = User.query.filter_by(usertype='Doctor').all()
    doctors_list = []
    for doc in doc_users:
        d_record = Doctors.query.filter_by(email=doc.email).first()
        doctors_list.append({
            'id': doc.id,
            'username': doc.username,
            'dept': d_record.dept if d_record else ''
        })

    return render_template('admin/admin_appointments.html',
                           appointments=appt_data,
                           doctors=doctors_list,
                           selected_date=selected_date,
                           selected_doctor=selected_doctor,
                           search_query=search_query,
                           today=today,
                           yesterday=yesterday,
                           total_appointments=Appointments.query.count(),
                           doctor_name=doctor_name)


@app.route('/admin/update_appointment_status', methods=['POST'])
@login_required
def admin_update_appointment_status():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))

    appointment_id = request.form.get('appointment_id')
    status = request.form.get('status')
    redirect_url = request.form.get('redirect_url', url_for('admin_appointments'))

    # Remap pending back to scheduled to match internal system logic if needed
    if status == 'Pending': status = 'Scheduled'

    a = Appointments.query.get(appointment_id)
    if a:
        a.slot = status
        db.session.commit()
        flash(f'Appointment status updated successfully.', 'success')

    return redirect(redirect_url)


@app.route('/admin/delete_appointment', methods=['POST'])
@login_required
def admin_delete_appointment():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))

    appointment_id = request.form.get('appointment_id')
    redirect_url = request.form.get('redirect_url', url_for('admin_appointments'))

    a = Appointments.query.get(appointment_id)
    if a:
        db.session.delete(a)
        db.session.commit()
        flash('Appointment deleted permanently.', 'danger')

    return redirect(redirect_url)


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
    # Redirects back to the page the form was submitted from
    return redirect(request.referrer or url_for('admin_dashboard'))


# ─────────────────────────────────────────────
# ADMIN / STAFF MANAGEMENT
# ─────────────────────────────────────────────

@app.route('/admin/staff')
@login_required
def admin_staff():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))

    # Fetch all admins. 
    # Optional: You can filter out the currently logged-in admin if you don't want them deleting themselves!
    admin_users = User.query.filter_by(usertype='Admin').all()
    
    return render_template('admin/admin_staff.html', admins=admin_users)

@app.route('/admin/edit_staff', methods=['POST'])
@login_required
def admin_edit_staff():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))

    staff_id = request.form.get('staff_id')
    username = request.form.get('username')
    email    = request.form.get('email')

    u = User.query.get(staff_id)
    if u and u.usertype == 'Admin':
        u.username = username
        u.email = email
        db.session.commit()
        flash(f'Administrator {username} updated successfully.', 'success')

    return redirect(url_for('admin_staff'))

@app.route('/admin/change_staff_password', methods=['POST'])
@login_required
def admin_change_staff_password():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))

    staff_id         = request.form.get('staff_id')
    new_password     = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if new_password != confirm_password:
        flash('Passwords do not match. Please try again.', 'danger')
        return redirect(url_for('admin_staff'))

    u = User.query.get(staff_id)
    if u and u.usertype == 'Admin':
        u.password = generate_password_hash(new_password)
        db.session.commit()
        flash('Administrator password updated successfully.', 'success')

    return redirect(url_for('admin_staff'))

@app.route('/admin/delete_staff', methods=['POST'])
@login_required
def admin_delete_staff():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))

    staff_id = request.form.get('staff_id')
    
    # Safety Check: Prevent the admin from deleting themselves
    if int(staff_id) == current_user.id:
        flash('Safety Protocol: You cannot delete your own active session.', 'warning')
        return redirect(url_for('admin_staff'))

    u = User.query.get(staff_id)
    if u and u.usertype == 'Admin':
        db.session.delete(u)
        db.session.commit()
        flash('Administrator account removed successfully.', 'success')

    return redirect(url_for('admin_staff'))

# ─────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', 'true').lower() == 'true')