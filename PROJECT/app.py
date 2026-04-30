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
from models import db, Test, User, Appointments, MedicalRecord, Doctors, Trigr

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
        ).order_by(Appointments.time.asc()).all()

        total_today = len(todays_appointments)

        # 🚨 THE NEW SMART QUEUE LOGIC
        live_queue = []
        current_patient = None
        next_patient = None
        
        completed_count = 0
        waiting_count = 0
        action_required_count = 0
        prescribed_apt_ids = []

        for apt in todays_appointments:
            # 1. Check if they are completely DONE
            has_record = MedicalRecord.query.filter_by(apt_id=apt.apt_id).first()
            if has_record or apt.slot == 'Completed':
                prescribed_apt_ids.append(apt.apt_id)
                completed_count += 1
                continue # Skip the live queue entirely!
                
            # 2. Check if they MISSED it
            if apt.slot == 'Missed':
                continue # Skip the live queue!

            # 3. If we are here, they belong in the LIVE QUEUE
            apt_time = datetime.strptime(apt.time, '%I:%M %p').time()
            
            # Check if their appointment time has arrived or passed
            apt.is_active = (apt_time <= now)

            if apt.is_active or apt.slot == 'Attended':
                action_required_count += 1
                if not current_patient:
                    current_patient = apt # The first active person is the CURRENT patient
            else:
                waiting_count += 1
                if not next_patient:
                    next_patient = apt # The first future person is UP NEXT

            live_queue.append(apt)

        formatted_date = today.strftime('%A, %b %d, %Y')

        return render_template('index.html', 
                               live_queue=live_queue, # Only passing active/waiting patients!
                               total_today=total_today,
                               current_patient=current_patient,
                               next_patient=next_patient,
                               waiting_count=waiting_count,
                               completed_count=completed_count,
                               action_required_count=action_required_count,
                               today_date=formatted_date,
                               prescribed_apt_ids=prescribed_apt_ids)

    return render_template('index.html')

# ── Doctors Directory ──────────────────────────
@app.route('/doctors', methods=['GET'])
@login_required
def doctors():
    all_doctors = Doctors.query.all()
    return render_template('doctor.html', all_doctors=all_doctors)

# ── API: Get Booked Slots ────────────────────
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

# ── Book Appointment ─────────────────────────
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

        if len(number) != 10 or not number.isdigit():
            flash("Please enter a valid 10-digit phone number.", "danger")
            return render_template('bookings/patient.html', doct=doct)

        if is_slot_booked(date, time, doctor):
            flash(f"Slot Unavailable: Dr. {doctor.capitalize()} is already booked at {time}. Please choose another slot.", "warning")
            return redirect(url_for('patient'))

        new_appointment = Appointments(
            email=email, name=name, gender=gender,
            slot=slot, disease=disease, time=time,
            date=date, dept=dept, number=number, doctor=doctor
        )
        db.session.add(new_appointment)
        db.session.commit()
        
        return redirect(url_for('booking_success', apt_id=new_appointment.apt_id))

    pre_dept = request.args.get('dept', '')
    pre_doc = request.args.get('doctor', '')

    return render_template('bookings/patient.html', doct=doct, pre_dept=pre_dept, pre_doc=pre_doc)

# ── Booking Success Page ─────────────────────
@app.route('/booking_success/<int:apt_id>')
@login_required
def booking_success(apt_id):
    appointment = Appointments.query.get_or_404(apt_id)
    
    if current_user.usertype != "Doctor" and appointment.email != current_user.email:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('index'))
        
    return render_template('bookings/booking_success.html', appointment=appointment)

# ── Mark Appointment as Missed ────────────────
@app.route('/mark_missed/<int:apt_id>', methods=['POST'])
@login_required
def mark_missed(apt_id):
    if current_user.usertype != "Doctor":
        flash("Unauthorized!", "danger")
        return redirect(url_for('dashboard'))

    appointment = Appointments.query.get_or_404(apt_id)
    
    # We repurpose the 'slot' column to act as our Status tracker!
    appointment.slot = 'Missed'
    db.session.commit()
    
    flash(f"Appointment for {appointment.name} marked as Missed.", "info")
    return redirect(request.referrer or url_for('dashboard'))

# ── Mark Appointment as Attended (Pending Rx) ──
@app.route('/mark_attended/<int:apt_id>', methods=['POST'])
@login_required
def mark_attended(apt_id):
    if current_user.usertype != "Doctor":
        flash("Unauthorized!", "danger")
        return redirect(url_for('dashboard'))

    appointment = Appointments.query.get_or_404(apt_id)
    appointment.slot = 'Attended'
    db.session.commit()
    
    flash(f"{appointment.name} marked as Attended. Prescription is now pending.", "success")
    return redirect(request.referrer or url_for('index'))

# ── Bookings Dashboard ───────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    from datetime import datetime

    if current_user.usertype == "Doctor":
        query = Appointments.query.filter_by(doctor=current_user.username).all()
    else:
        query = Appointments.query.filter_by(email=current_user.email).all()
    
    # 🚨 IRONCLAD SORTING: Combines Date and Time into a single precise timestamp! (Descending)
    query.sort(key=lambda x: datetime.strptime(f"{x.date} {x.time}", '%Y-%m-%d %I:%M %p'), reverse=True)

    # Get a list of all appointments that have a prescription
    records = MedicalRecord.query.all()
    prescribed_apt_ids = [r.apt_id for r in records]
    
    return render_template('bookings/booking.html', query=query, page_title="Complete Booking History", prescribed_apt_ids=prescribed_apt_ids)

# ── Upcoming Bookings ───────────────────────
@app.route('/upcoming_bookings')
@login_required
def upcoming_bookings():
    today = date.today()
    from datetime import datetime
    now = datetime.now().time()

    # 1. Fetch all appointments from today onwards
    if current_user.usertype == "Doctor":
        raw_query = Appointments.query.filter(
            Appointments.doctor == current_user.username, 
            Appointments.date >= today
        ).all()
    else:
        raw_query = Appointments.query.filter(
            Appointments.email == current_user.email, 
            Appointments.date >= today
        ).all()
    
    # Fetch medical records to catch "Legacy" appointments 
    records = MedicalRecord.query.all()
    prescribed_apt_ids = [r.apt_id for r in records]

    # 2. SMART FILTER: Remove past times, completed slots, AND existing records
    upcoming_list = []
    for apt in raw_query:
        # Convert string time to a real time object for comparison
        apt_time = datetime.strptime(apt.time, '%I:%M %p').time()
        
        # Skip if it is today AND the time has already passed
        if apt.date == today and apt_time <= now:
            continue
            
        # Skip if the doctor handled it, OR if a prescription already exists!
        if apt.slot in ['Completed', 'Missed', 'Attended'] or apt.apt_id in prescribed_apt_ids:
            continue

        upcoming_list.append(apt)
        
    # 3. IRONCLAD SORTING: Combines Date and Time! (Ascending - No reverse=True)
    upcoming_list.sort(key=lambda x: datetime.strptime(f"{x.date} {x.time}", '%Y-%m-%d %I:%M %p'))

    return render_template('bookings/booking.html', query=upcoming_list, page_title="Upcoming Appointments", prescribed_apt_ids=[])

# ── Medical Records ──────────────────────────
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
        
        # 🚨 Update the appointment status!
        appointment.slot = 'Completed'
        
        db.session.commit()
        
        flash("Medical record saved successfully!", "success")
        # Redirect to the home dashboard so the doctor sees the updated queue!
        return redirect(url_for('index'))
        
    return render_template('records/add_record.html', appointment=appointment)

@app.route('/view_record/<int:apt_id>')
@login_required
def view_record(apt_id):
    appointment = Appointments.query.get_or_404(apt_id)
    record = MedicalRecord.query.filter_by(apt_id=apt_id).first()
    
    # 🚨 FIX: Added .lower() to both sides to make the check bulletproof!
    if current_user.usertype == "Patient" and appointment.email.lower() != current_user.email.lower():
        flash("Unauthorized access to medical records.", "danger")
        return redirect(url_for('dashboard'))
    elif current_user.usertype == "Doctor" and appointment.doctor.lower() != current_user.username.lower():
         flash("Unauthorized access. You did not attend this patient.", "danger")
         return redirect(url_for('dashboard'))

    if not record:
        flash("No medical record has been generated for this appointment yet.", "info")
        return redirect(url_for('past_records'))
        
    return render_template('records/view_record.html', appointment=appointment, record=record)

# ── Edit Medical Record ──────────────────────
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

    # Security check: Only the doctor who wrote it can edit it!
    if appointment.doctor.lower() != current_user.username.lower():
         flash("Unauthorized access. You cannot edit another doctor's patient record.", "danger")
         return redirect(url_for('dashboard'))

    if request.method == "POST":
        record.diagnosis = request.form.get('diagnosis', '').strip()
        record.prescription = request.form.get('prescription', '').strip()
        record.notes = request.form.get('notes', '').strip()
        
        db.session.commit()
        flash(f"Medical record for {appointment.name} updated successfully!", "success")
        return redirect(url_for('past_records'))
        
    return render_template('records/edit_record.html', appointment=appointment, record=record)

@app.route('/past_records')
@login_required
def past_records():
    from datetime import datetime

    # 🚨 SMART FILTER: This is the "Patient History" route. 
    # It will ONLY show appointments that have a Medical Record attached.
    records = MedicalRecord.query.all()
    prescribed_apt_ids = [r.apt_id for r in records]

    # If no records exist at all yet, return empty
    if not prescribed_apt_ids:
        return render_template('bookings/booking.html', query=[], page_title="Completed Patient History", is_past_record=True, prescribed_apt_ids=[])

    if current_user.usertype == "Doctor":
        query = Appointments.query.filter(
            Appointments.apt_id.in_(prescribed_apt_ids), 
            Appointments.doctor == current_user.username
        ).all()
    else:
        query = Appointments.query.filter(
            Appointments.apt_id.in_(prescribed_apt_ids), 
            Appointments.email == current_user.email
        ).all()
    
    # 🚨 IRONCLAD SORTING: Combines Date and Time into a single precise timestamp! (Descending)
    query.sort(key=lambda x: datetime.strptime(f"{x.date} {x.time}", '%Y-%m-%d %I:%M %p'), reverse=True)

    return render_template('bookings/booking.html', query=query, page_title="Completed Patient History", is_past_record=True, prescribed_apt_ids=prescribed_apt_ids)

# ── Edit Booking ─────────────────────────────
@app.route('/edit/<int:apt_id>', methods=['POST', 'GET'])
@login_required
def edit(apt_id):
    post = Appointments.query.get_or_404(apt_id)
    doct = Doctors.query.all()

    if current_user.usertype != "Doctor" and post.email.lower() != current_user.email.lower():
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

# ── Delete Booking ────────────────────────────
@app.route('/delete/<int:apt_id>', methods=['POST'])
@login_required
def delete(apt_id):
    appointment = Appointments.query.get_or_404(apt_id)

    if current_user.usertype != "Doctor" and appointment.email.lower() != current_user.email.lower():
        flash("Unauthorized access.", "danger")
        return redirect(url_for('upcoming_bookings'))

    db.session.delete(appointment)
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

        # 1. Update Email (and sync with Doctors table if needed)
        if new_email != current_user.email:
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user:
                flash("That email address is already in use by another account.", "danger")
                return redirect(url_for('profile'))
            
            # 🚨 SYNCHRONIZATION: Update the Doctor Directory so they don't lose their patients!
            if current_user.usertype == 'Doctor':
                doc_record = Doctors.query.filter_by(email=current_user.email).first()
                if doc_record:
                    doc_record.email = new_email
            
            user.email = new_email

        # 2. Update Username (and sync with Doctors table)
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

    # 🚨 GET METHOD: Fetch the specific doctor record to display the Department
    doctor_info = None
    if current_user.usertype == 'Doctor':
        doctor_info = Doctors.query.filter_by(email=current_user.email).first()

    return render_template('auth/profile.html', doctor_info=doctor_info)

# ── Signup ────────────────────────────────────
@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == "POST":
        username = request.form.get('username', '').strip()
        usertype = "Patient"  # HARDCODED: All public signups are Patients now!
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

# ── SMART Context-Aware Search ────────────────
@app.route('/search', methods=['POST', 'GET'])
@login_required
def search():
    if request.method == "POST":
        query_str = request.form.get('search', '').strip()

        if not query_str:
            flash("Please enter a search term.", "warning")
            # Return them to wherever they searched from
            return redirect(request.referrer or url_for('index'))

        search_term = f"%{query_str}%"

        # 1. DOCTOR SEARCH LOGIC: Search their personal patients
        if current_user.usertype == 'Doctor':
            # Use .ilike() for case-insensitive matching against Name, Email, or Phone
            results = Appointments.query.filter(
                Appointments.doctor == current_user.username,
                (Appointments.name.ilike(search_term)) | 
                (Appointments.email.ilike(search_term)) | 
                (Appointments.number.ilike(search_term))
            ).order_by(Appointments.date.desc()).all()
            
            if not results:
                flash(f"No patients found matching '{query_str}'.", "warning")
                return redirect(request.referrer or url_for('index'))
                
            # Render the results in the standard booking table!
            return render_template('bookings/booking.html', query=results, page_title=f"Patient Search Results: '{query_str}'", prescribed_apt_ids=[r.apt_id for r in MedicalRecord.query.all()])

        # 2. PATIENT / ADMIN SEARCH LOGIC: Search Doctor Directory
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

# ── Admin Dashboard ───────────────────────────
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.usertype != "Admin":
        flash("Unauthorized Access! Administrator privileges required.", "danger")
        return redirect(url_for('index'))

    total_doctors = Doctors.query.count()
    total_users = User.query.filter_by(usertype='Patient').count()
    total_appointments = Appointments.query.count()
    
    recent_logs = Trigr.query.order_by(Trigr.tid.desc()).limit(5).all()

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
    app.run(debug=os.environ.get('FLASK_DEBUG', 'true').lower() == 'true')