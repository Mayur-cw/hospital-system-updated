# routes/admin.py
from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

# 🏥 UPGRADE: Imported Room and Admission models
from models import db, User, Appointments, Doctors, AuditLog, Billing, Room, Admission

admin_bp = Blueprint('admin', __name__)

# ── DASHBOARD ─────────────────────────────────────────────────────────

@admin_bp.route('/dashboard')
@login_required
def admin_dashboard():
    if current_user.usertype != "Admin":
        flash("Unauthorized Access! Administrator privileges required.", "danger")
        return redirect(url_for('main.index'))

    total_doctors = Doctors.query.count()
    total_users = User.query.filter_by(usertype='Patient').count()
    total_appointments = Appointments.query.count()
    recent_logs = AuditLog.query.order_by(AuditLog.tid.desc()).limit(5).all()

    # 🏥 UPGRADE: Fetch capacity stats for the dashboard
    total_rooms = Room.query.count()
    available_rooms = Room.query.filter_by(status='Available').count()
    occupied_rooms = Room.query.filter_by(status='Occupied').count()

    return render_template('admin/admin_dashboard.html', 
                           total_doctors=total_doctors, 
                           total_users=total_users, 
                           total_appointments=total_appointments,
                           recent_logs=recent_logs,
                           total_rooms=total_rooms,
                           available_rooms=available_rooms,
                           occupied_rooms=occupied_rooms)

# ── AUDIT LOGS ────────────────────────────────────────────────────────

@admin_bp.route('/details')
@login_required
def details():
    if current_user.usertype != "Admin":
        flash("Unauthorized Access!", "danger")
        return redirect(url_for('main.index'))

    logs_data = db.session.query(AuditLog, User).outerjoin(User, AuditLog.user_id == User.id).order_by(AuditLog.tid.desc()).all()
    
    posts = []
    for log, user in logs_data:
        posts.append({
            'tid': log.tid,
            'pid': log.user_id,
            'action': log.action,
            'timestamp': log.timestamp,
            'email': user.email if user else 'Deleted/Unknown',
            'name': user.username if user else 'Deleted/Unknown'
        })

    return render_template('admin/audit_logs.html', posts=posts)

# ── SYSTEM STAFF ──────────────────────────────────────────────────────

@admin_bp.route('/staff')
@login_required
def admin_staff():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    admin_users = User.query.filter_by(usertype='Admin').all()
    return render_template('admin/admin_staff.html', admins=admin_users)

@admin_bp.route('/add_staff', methods=['POST'])
@login_required
def add_staff():
    if current_user.usertype != "Admin":
        flash("Unauthorized! Only Admins can create staff accounts.", "danger")
        return redirect(url_for('main.index'))

    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    usertype = request.form.get('usertype', '').strip()
    dept = request.form.get('dept', '').strip()

    if User.query.filter_by(email=email).first():
        flash("An account with that email already exists.", "warning")
        return redirect(url_for('admin.admin_dashboard'))

    hashed_password = generate_password_hash(password)
    new_user = User(username=username, usertype=usertype, email=email, password=hashed_password)
    db.session.add(new_user)
    
    db.session.flush()
    
    if usertype == "Doctor":
        new_doc = Doctors(user_id=new_user.id, dept=dept)
        db.session.add(new_doc)
        
    db.session.commit()
    flash(f"Success! {usertype} account for {username} has been provisioned.", "success")
    return redirect(request.referrer or url_for('admin.admin_dashboard'))

@admin_bp.route('/edit_staff', methods=['POST'])
@login_required
def admin_edit_staff():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    staff_id = request.form.get('staff_id')
    username = request.form.get('username')
    email    = request.form.get('email')

    u = User.query.get(staff_id)
    if u and u.usertype == 'Admin':
        u.username = username
        u.email = email
        db.session.commit()
        flash(f'Administrator {username} updated successfully.', 'success')

    return redirect(url_for('admin.admin_staff'))

@admin_bp.route('/change_staff_password', methods=['POST'])
@login_required
def admin_change_staff_password():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    staff_id         = request.form.get('staff_id')
    new_password     = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if new_password != confirm_password:
        flash('Passwords do not match. Please try again.', 'danger')
        return redirect(url_for('admin.admin_staff'))

    u = User.query.get(staff_id)
    if u and u.usertype == 'Admin':
        u.password = generate_password_hash(new_password)
        db.session.commit()
        flash('Administrator password updated successfully.', 'success')

    return redirect(url_for('admin.admin_staff'))

@admin_bp.route('/delete_staff', methods=['POST'])
@login_required
def admin_delete_staff():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    staff_id = request.form.get('staff_id')
    
    if int(staff_id) == current_user.id:
        flash('Safety Protocol: You cannot delete your own active session.', 'warning')
        return redirect(url_for('admin.admin_staff'))

    u = User.query.get(staff_id)
    if u and u.usertype == 'Admin':
        db.session.delete(u)
        db.session.commit()
        flash('Administrator account removed successfully.', 'success')

    return redirect(url_for('admin.admin_staff'))

# ── DOCTORS DIRECTORY ─────────────────────────────────────────────────

@admin_bp.route('/doctors')
@login_required
def admin_doctors():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    doc_users = User.query.filter_by(usertype='Doctor').all()
    doctors_list = []
    for u in doc_users:
        doc_record = Doctors.query.filter_by(user_id=u.id).first()
        doctors_list.append({
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'dept': doc_record.dept if doc_record else 'Unassigned'
        })

    return render_template('admin/admin_doctors.html', doctors=doctors_list)

@admin_bp.route('/edit_doctor', methods=['POST'])
@login_required
def admin_edit_doctor():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    doctor_id = request.form.get('doctor_id')
    username  = request.form.get('username')
    email     = request.form.get('email')
    dept      = request.form.get('dept')

    u = User.query.get(doctor_id)
    if u and u.usertype == 'Doctor':
        u.username = username
        u.email = email
        
        doc = Doctors.query.filter_by(user_id=u.id).first()
        if doc:
            doc.dept = dept
            
        db.session.commit()
        flash(f'Doctor {username} updated successfully.', 'success')

    return redirect(url_for('admin.admin_doctors'))

@admin_bp.route('/change_doctor_password', methods=['POST'])
@login_required
def admin_change_doctor_password():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    doctor_id        = request.form.get('doctor_id')
    new_password     = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if new_password != confirm_password:
        flash('Passwords do not match. Please try again.', 'danger')
        return redirect(url_for('admin.admin_doctors'))

    u = User.query.get(doctor_id)
    if u and u.usertype == 'Doctor':
        u.password = generate_password_hash(new_password)
        db.session.commit()
        flash('Doctor password updated successfully.', 'success')

    return redirect(url_for('admin.admin_doctors'))

@admin_bp.route('/delete_doctor', methods=['POST'])
@login_required
def admin_delete_doctor():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    doctor_id = request.form.get('doctor_id')
    u = User.query.get(doctor_id)
    if u and u.usertype == 'Doctor':
        doc = Doctors.query.filter_by(user_id=u.id).first()
        if doc:
            db.session.delete(doc)
        db.session.delete(u)
        db.session.commit()
        flash('Doctor account removed successfully.', 'success')

    return redirect(url_for('admin.admin_doctors'))

# ── PATIENTS DIRECTORY ────────────────────────────────────────────────

@admin_bp.route('/patients')
@login_required
def admin_patients():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

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

# ── APPOINTMENTS ──────────────────────────────────────────────────────

@admin_bp.route('/appointments')
@login_required
def admin_appointments():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    
    search_query = request.args.get('search', '').strip()
    default_date = 'all' if search_query else today
    
    selected_date = request.args.get('date', default_date)
    selected_doctor = request.args.get('doctor_id', '')

    q = Appointments.query

    if selected_date and selected_date != 'all':
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

    appts = q.order_by(Appointments.date.desc(), Appointments.time.asc()).all()

    appt_data = []
    for a in appts:
        u = User.query.get(a.user_id)
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

    doc_users = User.query.filter_by(usertype='Doctor').all()
    doctors_list = []
    for doc in doc_users:
        d_record = Doctors.query.filter_by(user_id=doc.id).first()
        doctors_list.append({
            'id': doc.id,
            'username': doc.username,
            'dept': d_record.dept if d_record else 'Unassigned'
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

@admin_bp.route('/update_appointment_status', methods=['POST'])
@login_required
def admin_update_appointment_status():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    appointment_id = request.form.get('appointment_id')
    status = request.form.get('status')
    redirect_url = request.form.get('redirect_url', url_for('admin.admin_appointments'))

    if status == 'Pending': status = 'Scheduled'

    a = Appointments.query.get(appointment_id)
    if a:
        a.slot = status
        db.session.commit()
        flash(f'Appointment status updated successfully.', 'success')

    return redirect(redirect_url)

@admin_bp.route('/delete_appointment', methods=['POST'])
@login_required
def admin_delete_appointment():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    appointment_id = request.form.get('appointment_id')
    redirect_url = request.form.get('redirect_url', url_for('admin.admin_appointments'))

    a = Appointments.query.get(appointment_id)
    if a:
        db.session.delete(a)
        db.session.commit()
        flash('Appointment deleted permanently.', 'danger')

    return redirect(redirect_url)


# ── FINANCIALS & BILLING ──────────────────────────────────────────────

@admin_bp.route('/financials')
@login_required
def admin_financials():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    all_bills = Billing.query.order_by(Billing.issued_on.desc()).all()
    
    total_collected = sum(bill.amount for bill in all_bills if bill.status == 'Paid')
    pending_revenue = sum(bill.amount for bill in all_bills if bill.status == 'Unpaid')
    
    return render_template('admin/admin_financials.html', 
                           bills=all_bills, 
                           total_collected=total_collected, 
                           pending_revenue=pending_revenue)

@admin_bp.route('/financials/<int:bill_id>/invoice')
@login_required
def view_invoice(bill_id):
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))
        
    invoice = Billing.query.get_or_404(bill_id)
    return render_template('admin/admin_view_invoice.html', invoice=invoice)

@admin_bp.route('/financials/<int:bill_id>/receipt')
@login_required
def view_receipt(bill_id):
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))
        
    invoice = Billing.query.get_or_404(bill_id)
    return render_template('bookings/receipt.html', invoice=invoice)

# 🏥 ── ROOM & WARD MANAGEMENT ─────────────────────────────────────────

@admin_bp.route('/rooms')
@login_required
def admin_rooms():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    all_rooms = Room.query.order_by(Room.room_number).all()
    
    # 🚨 NEW: Fetch active admissions to display in the UI table
    active_admissions = Admission.query.filter_by(status='Admitted').order_by(Admission.admission_date.desc()).all()
    
    total_rooms = len(all_rooms)
    available_rooms = sum(1 for r in all_rooms if r.status == 'Available')
    occupied_rooms = sum(1 for r in all_rooms if r.status == 'Occupied')
    maintenance_rooms = sum(1 for r in all_rooms if r.status == 'Maintenance')

    return render_template('admin/admin_rooms.html', 
                           rooms=all_rooms,
                           active_admissions=active_admissions,
                           total_rooms=total_rooms,
                           available_rooms=available_rooms,
                           occupied_rooms=occupied_rooms,
                           maintenance_rooms=maintenance_rooms)

@admin_bp.route('/add_room', methods=['POST'])
@login_required
def add_room():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    room_number = request.form.get('room_number').strip()
    ward_type = request.form.get('ward_type').strip()
    rate_per_day = request.form.get('rate_per_day').strip()

    if Room.query.filter_by(room_number=room_number).first():
        flash(f"Room {room_number} already exists.", "danger")
        return redirect(url_for('admin.admin_rooms'))

    try:
        new_room = Room(room_number=room_number, ward_type=ward_type, rate_per_day=float(rate_per_day))
        db.session.add(new_room)
        db.session.commit()
        flash(f"Room {room_number} successfully added to the {ward_type} ward.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding room. Please check input values.", "danger")

    return redirect(url_for('admin.admin_rooms'))

@admin_bp.route('/edit_room', methods=['POST'])
@login_required
def edit_room():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    room_id = request.form.get('room_id')
    room = Room.query.get_or_404(room_id)
    
    room.room_number = request.form.get('room_number').strip()
    room.ward_type = request.form.get('ward_type').strip()
    room.rate_per_day = float(request.form.get('rate_per_day').strip())
    
    new_status = request.form.get('status').strip()
    if room.status == 'Occupied' and new_status != 'Occupied':
        flash(f"Cannot manually change status of Room {room.room_number}. It must be freed by a patient discharge.", "warning")
    else:
        room.status = new_status
        
    db.session.commit()
    flash(f"Room {room.room_number} details updated.", "success")
    return redirect(url_for('admin.admin_rooms'))
    
@admin_bp.route('/delete_room', methods=['POST'])
@login_required
def delete_room():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))
        
    room_id = request.form.get('room_id')
    room = Room.query.get_or_404(room_id)
    
    if room.status == 'Occupied':
        flash(f"Cannot delete Room {room.room_number} because a patient is currently admitted there.", "danger")
    else:
        db.session.delete(room)
        db.session.commit()
        flash(f"Room {room.room_number} has been removed from the system.", "success")
        
    return redirect(url_for('admin.admin_rooms'))

# 🚨 NEW: THE DISCHARGE ROUTE 🚨
@admin_bp.route('/discharge', methods=['POST'])
@login_required
def discharge_patient():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))
        
    admission_id = request.form.get('admission_id')
    admission = Admission.query.get_or_404(admission_id)
    
    if admission.status == 'Discharged':
        flash(f"Patient {admission.patient.username} has already been discharged.", "info")
        return redirect(url_for('admin.admin_rooms'))
        
    # Mark as discharged and record the timestamp
    admission.status = 'Discharged'
    admission.discharge_date = db.func.now()
    
    # 🎓 DBMS POWER MOVE: The `admission_update` MySQL trigger we built
    # will automatically intercept this commit and flip the room's status back to 'Available'!
    db.session.commit()
    
    flash(f"Patient {admission.patient.username} has been officially discharged. Room {admission.room.room_number} is now Available.", "success")
    return redirect(url_for('admin.admin_rooms'))